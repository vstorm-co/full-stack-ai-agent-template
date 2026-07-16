{% raw %}"use client";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, ExternalLink, Globe, Lock, RotateCw, Search } from "lucide-react";
import { cleanPageText, parseFetchedPage } from "@/lib/py-literal";
import { MarkdownContent } from "../markdown-content";
import { cn } from "@/lib/utils";
import type { WebSearchPayload } from "./web-search";

/**
 * BrowserStage / BrowserSession — a synthetic, animated browser window that *visualizes*
 * what the agent did on the web, driven purely by the tool's own data (real queries, URLs,
 * results and — when captured — real page screenshots). There is NO live browser behind it;
 * the moving cursor is a frontend sprite (CDP screencast wouldn't capture a real one anyway).
 *
 * A BrowserSession is ONE window playing the whole multi-step browse as a single, strictly
 * sequential scene: type the query → results page → click hit #1 → open that page → scan it →
 * back to results → click hit #2 → … Each step awaits the previous, so nothing overlaps and
 * every page is watchable. Honors prefers-reduced-motion by jumping to the end state.
 */

export interface FollowUp {
  url: string;
  content: string;
  /** A real screenshot of the page (data URI). When present it's shown instead of the
   *  reconstructed markdown — the actual page the agent opened, captured at browse time. */
  screenshot?: string;
}

const reduceMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Real favicons for real domains — the cheapest 50% of the "wow". Falls back to a
// globe glyph on error (the export makes one external request per icon at view time).
function faviconFor(url: string): string | null {
  const host = domainOf(url);
  if (!host || host === url) return null;
  return `https://icons.duckduckgo.com/ip3/${host}.ico`;
}

const CURSOR_PATH = "M2 2 L2 20 L7 15 L10.5 22 L13 21 L9.5 14 L16 14 Z";

// Choreography timing (ms). Tuned snappy — the whole browse plays in one sitting.
// SPEED scales the whole sequence (higher = faster); browseSessionDurationMs derives from these,
// so the replay pacing follows automatically.
const SPEED = 2.0;
const T = (ms: number) => Math.round(ms / SPEED);
const TIMING = {
  boot: T(200),
  focus: T(333),
  typeChar: T(15),
  afterType: T(120),
  loading: T(367),
  serp: T(300),
  hover: T(300),
  click: T(133),
  navLoad: T(367),
  preScan: T(187),
  scan: T(1000),
  dwell: T(433),
  back: T(333),
};

/** Rough total duration of a BrowserSession run — used to size replay pacing. */
export function browseSessionDurationMs(query: string, visitCount: number): number {
  let d = TIMING.boot + TIMING.focus + query.length * TIMING.typeChar + TIMING.afterType + TIMING.loading + TIMING.serp;
  for (let i = 0; i < visitCount; i += 1) {
    d += TIMING.hover + TIMING.click + TIMING.navLoad + TIMING.preScan + TIMING.scan + TIMING.dwell + TIMING.back;
  }
  return d;
}

/** One pass of "reading" a page: scroll the container to the bottom while the cursor
 *  drifts down it. Resolves when done (or immediately if there's nothing to scroll). */
function scanTween(opts: {
  scrollEl: HTMLElement;
  wrapEl: HTMLElement | null;
  setCursor: (p: { x: number; y: number }) => void;
  isCancelled: () => boolean;
  onRaf: (id: number) => void;
  dur?: number;
}): Promise<void> {
  const { scrollEl, wrapEl, setCursor, isCancelled, onRaf, dur = TIMING.scan } = opts;
  return new Promise((resolve) => {
    const target = Math.max(0, scrollEl.scrollHeight - scrollEl.clientHeight);
    if (target <= 0) {
      resolve();
      return;
    }
    const start = performance.now();
    const step = (now: number) => {
      if (isCancelled()) {
        resolve();
        return;
      }
      const t = Math.min(1, (now - start) / dur);
      const eased = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
      scrollEl.scrollTop = target * eased;
      if (wrapEl) {
        const w = wrapEl.getBoundingClientRect();
        const s = scrollEl.getBoundingClientRect();
        setCursor({ x: s.left - w.left + s.width * 0.5, y: s.top - w.top + s.height * (0.35 + 0.5 * eased) });
      }
      if (t < 1) {
        const id = requestAnimationFrame(step);
        onRaf(id);
      } else {
        resolve();
      }
    };
    const id = requestAnimationFrame(step);
    onRaf(id);
  });
}

/** The animated pointer sprite + click ripple, positioned over the stage. */
function Cursor({ x, y, clicking, visible }: { x: number; y: number; clicking: boolean; visible: boolean }) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute top-0 left-0 z-30"
      style={{
        transform: `translate(${x}px, ${y}px)`,
        transition: "transform 620ms cubic-bezier(0.22, 1, 0.36, 1), opacity 300ms ease",
        opacity: visible ? 1 : 0,
      }}
    >
      <span
        className="absolute rounded-full"
        style={{
          left: -7,
          top: -7,
          width: 14,
          height: 14,
          background: "oklch(from var(--color-brand) l c h / 0.35)",
          transform: clicking ? "scale(2.6)" : "scale(0)",
          opacity: clicking ? 0 : 0.9,
          transition: "transform 400ms ease-out, opacity 400ms ease-out",
        }}
      />
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        className="relative"
        style={{ filter: "drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.45))" }}
      >
        <path d={CURSOR_PATH} fill="white" stroke="black" strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </div>
  );
}

/** The browser chrome: traffic lights, a tab, and the address bar. */
function Chrome({
  tabTitle,
  tabFavicon,
  address,
  typedAddress,
  loading,
  children,
}: {
  tabTitle: string;
  tabFavicon: string | null;
  address: string;
  typedAddress: string;
  loading: boolean;
  children: React.ReactNode;
}) {
  const [faviconOk, setFaviconOk] = useState(true);
  return (
    <div className="border-border/70 bg-muted/60 overflow-hidden rounded-xl border shadow-sm">
      {/* Tab strip */}
      <div className="border-border/50 flex items-end gap-1 border-b px-2 pt-2">
        <span className="mb-2 flex shrink-0 items-center gap-1.5 pr-1">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        </span>
        <span className="border-border/60 bg-card text-foreground/80 flex min-w-0 max-w-[220px] items-center gap-1.5 rounded-t-lg border border-b-0 px-2.5 py-1.5 text-xs">
          {tabFavicon && faviconOk ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={tabFavicon}
              alt=""
              width={13}
              height={13}
              className="h-[13px] w-[13px] shrink-0 rounded-sm"
              onError={() => setFaviconOk(false)}
            />
          ) : (
            <Globe className="text-foreground/50 h-3 w-3 shrink-0" />
          )}
          <span className="truncate">{tabTitle}</span>
        </span>
      </div>
      {/* Toolbar / address bar */}
      <div className="flex items-center gap-2 px-2.5 py-2">
        <RotateCw className={cn("text-foreground/40 h-3.5 w-3.5 shrink-0", loading && "animate-spin")} />
        <div className="border-border/60 bg-background text-foreground/70 flex min-w-0 flex-1 items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[11px]">
          <Lock className="h-3 w-3 shrink-0 text-emerald-500" />
          <span className="truncate">
            {typedAddress || <span className="text-foreground/30">{address}</span>}
          </span>
        </div>
      </div>
      {/* Viewport */}
      <div className="bg-background relative">
        {loading && (
          <div className="bg-border/40 absolute inset-x-0 top-0 z-20 h-0.5 overflow-hidden">
            <div className="bg-brand h-full w-1/3 animate-[browser-load_1.1s_ease-in-out_infinite]" />
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

/** A small favicon that falls back to a globe glyph on load error. */
function FavIcon({ url }: { url: string }) {
  const [ok, setOk] = useState(true);
  const src = faviconFor(url);
  if (!src || !ok) return <Globe className="text-foreground/40 h-3 w-3 shrink-0" />;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      width={12}
      height={12}
      className="h-3 w-3 shrink-0 rounded-sm"
      onError={() => setOk(false)}
    />
  );
}

/** The opened page inside the viewport: a real screenshot when we have one, else the
 *  reconstructed markdown + a source link. Scrolls (the cursor scans it). */
function PageBody({
  url,
  content,
  screenshot,
  scrollRef,
  visible,
}: {
  url: string;
  content: string;
  screenshot?: string;
  scrollRef: React.Ref<HTMLDivElement>;
  visible: boolean;
}) {
  // `web_fetch` returns a Python-repr `{url,title,content}` dict — render just the readable page
  // text (JS/CSS boilerplate stripped), never the raw repr blob.
  const page = parseFetchedPage(content);
  const body = cleanPageText(page ? page.content : content);
  return (
    <div
      ref={scrollRef}
      className={cn(
        "h-[300px] overflow-y-auto transition-opacity duration-500",
        visible ? "opacity-100" : "opacity-0",
      )}
    >
      {screenshot ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={screenshot} alt={domainOf(url)} className="block w-full select-none" draggable={false} />
      ) : (
        <div className="px-4 py-3">
          <div className="prose-sm max-w-none text-sm">
            <MarkdownContent content={body} />
          </div>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground/45 hover:text-brand mt-3 inline-flex items-center gap-1 text-[11px]"
          >
            <ExternalLink className="h-3 w-3" /> {url}
          </a>
        </div>
      )}
    </div>
  );
}

/** The inner content of a SERP row — favicon/domain, title, snippet. */
function SerpRowBody({
  hit,
  showChevron,
  open,
}: {
  hit: WebSearchPayload["results"][number];
  showChevron?: boolean;
  open?: boolean;
}) {
  return (
    <>
      <div className="mb-0.5 flex items-center gap-1.5">
        <FavIcon url={hit.url} />
        <span className="text-foreground/45 truncate text-[11px]">{domainOf(hit.url)}</span>
        {showChevron && (
          <ChevronDown
            className={cn(
              "text-foreground/35 ml-auto h-3.5 w-3.5 shrink-0 transition-transform",
              open && "rotate-180",
            )}
          />
        )}
      </div>
      <p className="truncate text-sm font-medium text-[#1a0dab] dark:text-[#8ab4f8]">{hit.title}</p>
      {hit.content && (
        <p className="text-foreground/55 mt-0.5 line-clamp-2 text-[11px] leading-relaxed">{hit.content}</p>
      )}
    </>
  );
}

/** A settled SERP row: click to reveal the scrollable page snapshot; click the snapshot to open
 *  the real page in a new tab. Falls back to a plain external link when there's no screenshot. */
function SerpRowInteractive({
  hit,
  screenshot,
}: {
  hit: WebSearchPayload["results"][number];
  screenshot?: string;
}) {
  const [open, setOpen] = useState(false);
  const host = domainOf(hit.url);
  if (!screenshot) {
    return (
      <a
        href={hit.url}
        target="_blank"
        rel="noopener noreferrer"
        className="hover:bg-foreground/[0.03] block rounded-lg px-2 py-1.5 transition-colors"
      >
        <SerpRowBody hit={hit} />
      </a>
    );
  }
  return (
    <div className="rounded-lg">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="hover:bg-foreground/[0.03] block w-full rounded-lg px-2 py-1.5 text-left transition-colors"
      >
        <SerpRowBody hit={hit} showChevron open={open} />
      </button>
      {open && (
        <a
          href={hit.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`Open ${host}`}
          className="border-border/60 bg-background hover:border-brand/50 group mx-2 mt-1 mb-1 block overflow-hidden rounded-lg border transition-colors"
        >
          <div className="text-foreground/45 border-border/50 group-hover:text-brand flex items-center gap-1.5 border-b px-2.5 py-1 font-mono text-[9px] tracking-wider uppercase">
            <span className="truncate">{host}</span>
            <span>·</span>
            <span>open page</span>
            <ExternalLink className="ml-auto h-3 w-3 shrink-0" />
          </div>
          <div className="max-h-64 overflow-y-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={screenshot} alt={host} className="block w-full select-none" draggable={false} />
          </div>
        </a>
      )}
    </div>
  );
}

/** The results page: one row per hit, with visited/active accents the cursor drives. Once the
 *  browse has settled (`interactive`), rows expand into a clickable page snapshot instead. */
function Serp({
  results,
  hovered,
  resultRefs,
  interactive = false,
  screenshots,
}: {
  results: WebSearchPayload["results"];
  hovered: number | null;
  resultRefs: React.MutableRefObject<(HTMLAnchorElement | null)[]>;
  interactive?: boolean;
  screenshots?: (string | undefined)[];
}) {
  // Settled SERP: show the top few hits, collapse the long tail (DuckDuckGo returns ~40) behind
  // a "+N more" toggle so the results page stays compact instead of scrolling on forever.
  const PREVIEW_COUNT = 3;
  const [showAll, setShowAll] = useState(false);
  if (interactive) {
    const hasMore = results.length > PREVIEW_COUNT;
    const visible = showAll ? results : results.slice(0, PREVIEW_COUNT);
    const rest = results.length - PREVIEW_COUNT;
    return (
      <div className="space-y-2.5">
        {visible.map((hit, i) => (
          <SerpRowInteractive key={`${hit.url}-${i}`} hit={hit} screenshot={screenshots?.[i]} />
        ))}
        {hasMore && (
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="text-foreground/55 hover:text-foreground hover:bg-foreground/[0.04] border-border/50 flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed px-2 py-2 text-xs font-medium transition-colors"
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", showAll && "rotate-180")} />
            {showAll ? "Show fewer results" : `+${rest} more result${rest !== 1 ? "s" : ""}`}
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-2.5">
      {results.map((hit, i) => (
        <a
          key={`${hit.url}-${i}`}
          ref={(el) => {
            resultRefs.current[i] = el;
          }}
          href={hit.url}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "browser-result-in block rounded-lg px-2 py-1.5 transition-colors",
            hovered === i ? "bg-brand/[0.06]" : "hover:bg-foreground/[0.03]",
          )}
          style={{ animationDelay: `${i * 90}ms` }}
        >
          <SerpRowBody hit={hit} />
        </a>
      ))}
    </div>
  );
}

type Screen = "blank" | "loading" | "serp" | "page";

/** One browser window that plays the whole multi-step browse sequentially:
 *  search → open each visited result in turn → scan it → back → next. */
export function BrowserSession({
  query,
  results,
  visits,
  onComplete,
  onProgress,
  instant = false,
}: {
  query: string;
  results: WebSearchPayload["results"];
  visits: FollowUp[];
  /** Fired once when the whole browse animation has played out (or immediately under
   *  reduced motion / instant). Lets the replay hold the response until browsing finishes. */
  onComplete?: () => void;
  /** Fired with the page index as each visit begins, so the chat card's spinner can mirror the
   *  animation's current page (true sync when the panel is open). */
  onProgress?: (visitIndex: number) => void;
  /** Skip the choreography and render the finished end state directly — the results page with
   *  the full results page. Used when the panel is opened after the answer is done,
   *  so the scene isn't replayed from scratch. */
  instant?: boolean;
}) {
  const stageRef = useRef<HTMLDivElement>(null);
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const resultRefs = useRef<(HTMLAnchorElement | null)[]>([]);
  const pageScrollRef = useRef<HTMLDivElement>(null);
  const visitsRef = useRef(visits);
  visitsRef.current = visits;
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  const onProgressRef = useRef(onProgress);
  onProgressRef.current = onProgress;
  const doneRef = useRef(false);
  const finish = () => {
    if (doneRef.current) return;
    doneRef.current = true;
    onCompleteRef.current?.();
  };

  // Instant mounts already showing the finished results page — no blank→serp flash.
  const [screen, setScreen] = useState<Screen>(instant ? "serp" : "blank");
  const [typed, setTyped] = useState(instant ? query.length : 0);
  const [current, setCurrent] = useState(0);
  const [hovered, setHovered] = useState<number | null>(null);
  const [addr, setAddr] = useState(instant ? query : "");
  // Once settled, the results page grows to fit all rows and they become clickable snapshot expanders.
  const [settled, setSettled] = useState(instant);
  const [tab, setTab] = useState(query || "Search");
  const [cursor, setCursor] = useState({ x: 44, y: 150 });
  const [cursorVisible, setCursorVisible] = useState(false);
  const [clicking, setClicking] = useState(false);

  const moveTo = (el: HTMLElement | null) => {
    const stage = stageRef.current;
    if (!stage || !el) return;
    const s = stage.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    setCursor({ x: r.left - s.left + r.width / 2, y: r.top - s.top + r.height / 2 });
  };

  useEffect(() => {
    let cancelled = false;
    let raf = 0;
    const timers: number[] = [];
    const sleep = (ms: number) => new Promise<void>((res) => timers.push(window.setTimeout(res, ms)));
    const stop = () => cancelled;

    // The finished resting state: back on the results page.
    const settleOnResults = () => {
      setTyped(query.length);
      setHovered(null);
      setCurrent(0);
      setTab(query || "Search");
      setAddr(query);
      setScreen("serp");
      setSettled(true);
    };

    (async () => {
      if (instant || reduceMotion()) {
        settleOnResults();
        finish();
        return;
      }

      onProgressRef.current?.(0); // park the chat spinner on the first page during the search phase
      await sleep(TIMING.boot);
      if (stop()) return;
      setCursorVisible(true);
      moveTo(searchBoxRef.current);
      await sleep(TIMING.focus);
      if (stop()) return;

      // Type the query into the search box + address bar.
      for (let i = 1; i <= query.length; i += 1) {
        await sleep(TIMING.typeChar);
        if (stop()) return;
        setTyped(i);
        setAddr(query.slice(0, i));
      }
      await sleep(TIMING.afterType);
      if (stop()) return;
      setScreen("loading");
      await sleep(TIMING.loading);
      if (stop()) return;
      setScreen("serp");
      await sleep(TIMING.serp);
      if (stop()) return;

      // Visit each result in turn — click, open, scan, back.
      let vi = 0;
      while (vi < visitsRef.current.length) {
        const v = visitsRef.current[vi];
        if (!v) break;
        onProgressRef.current?.(vi); // chat spinner follows the page being opened
        setHovered(vi);
        moveTo(resultRefs.current[vi] ?? null);
        await sleep(TIMING.hover);
        if (stop()) return;
        setClicking(true);
        await sleep(TIMING.click);
        if (stop()) return;
        setClicking(false);

        // Navigate to the page in the same window.
        setCurrent(vi);
        setTab(domainOf(v.url));
        setAddr(v.url);
        setScreen("loading");
        await sleep(TIMING.navLoad);
        if (stop()) return;
        setScreen("page");
        await sleep(TIMING.preScan);
        if (stop()) return;
        if (pageScrollRef.current) {
          await scanTween({
            scrollEl: pageScrollRef.current,
            wrapEl: stageRef.current,
            setCursor,
            isCancelled: stop,
            onRaf: (id) => (raf = id),
          });
        }
        if (stop()) return;
        await sleep(TIMING.dwell); // dwell at the bottom so the page is actually watchable
        if (stop()) return;
        vi += 1;

        // Back to results — for the next one, or to settle on the finished results page.
        setHovered(null);
        setTab(query || "Search");
        setAddr(query);
        setScreen("serp");
        await sleep(TIMING.back);
        if (stop()) return;
      }
      // Rest on the results page — the watchable end state.
      settleOnResults();
      finish();
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      timers.forEach((t) => clearTimeout(t));
    };
    // Re-run when `instant` flips: false→true (browse phase ended) cancels the in-flight
    // choreography and jumps straight to the settled results page, so the panel stops exactly
    // when the chat does. Mounting with instant=true (panel opened after the browse) shows the
    // finished page directly — never a replay from scratch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instant]);

  const onPage = screen === "page";
  const active = visits[current];
  // Page snapshot for each result row (settled SERP), matched by URL, then by position.
  const shotForResult = results.map((r, i) => visits.find((v) => v.url === r.url)?.screenshot ?? visits[i]?.screenshot);

  return (
    <div ref={stageRef} className="relative">
      <Chrome
        tabTitle={onPage && active ? tab : query || "Search"}
        tabFavicon={onPage && active ? faviconFor(active.url) : null}
        address="https://search — type a query…"
        typedAddress={addr}
        loading={screen === "loading"}
      >
        {onPage && active ? (
          <PageBody
            url={active.url}
            content={active.content}
            screenshot={active.screenshot}
            scrollRef={pageScrollRef}
            visible
          />
        ) : (
          <div className={cn("px-4 py-4", settled ? "min-h-[300px]" : "h-[300px] overflow-hidden")}>
            <div
              ref={searchBoxRef}
              className="border-border/60 bg-muted/40 mb-4 flex items-center gap-2 rounded-full border px-3.5 py-2"
            >
              <Search className="text-foreground/40 h-3.5 w-3.5 shrink-0" />
              <span className="text-foreground/75 min-w-0 flex-1 truncate text-sm">
                {query.slice(0, typed)}
                {(screen === "blank" || typed < query.length) && (
                  <span className="bg-brand ml-0.5 inline-block h-3.5 w-px animate-pulse align-middle" />
                )}
              </span>
            </div>

            {screen === "serp" ? (
              <Serp
                results={results}
                hovered={hovered}
                resultRefs={resultRefs}
                interactive={settled}
                screenshots={shotForResult}
              />
            ) : (
              <div className="text-foreground/35 flex h-[200px] flex-col items-center justify-center gap-2 text-xs">
                <Globe className={cn("h-6 w-6", screen === "loading" && "animate-pulse")} />
                {screen === "loading" ? "Searching the web…" : "Ready"}
              </div>
            )}
          </div>
        )}
      </Chrome>
      <Cursor x={cursor.x} y={cursor.y} clicking={clicking} visible={cursorVisible} />
    </div>
  );
}

type ReadPhase = "boot" | "loading" | "page" | "done";

/** Read mode (a standalone fetch_url with no preceding search): open the URL, then scan it. */
function ReadStage({ url, content, screenshot }: { url: string; content: string; screenshot?: string }) {
  const stageRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<ReadPhase>("boot");
  const [cursor, setCursor] = useState({ x: 60, y: 90 });
  const [cursorVisible, setCursorVisible] = useState(false);
  const host = domainOf(url);

  useEffect(() => {
    let cancelled = false;
    let raf = 0;
    const timers: number[] = [];
    const sleep = (ms: number) => new Promise<void>((res) => timers.push(window.setTimeout(res, ms)));

    (async () => {
      if (reduceMotion()) {
        setPhase("done");
        return;
      }
      await sleep(350);
      if (cancelled) return;
      setCursorVisible(true);
      setPhase("loading");
      await sleep(1000);
      if (cancelled) return;
      setPhase("page");
      await sleep(600);
      if (cancelled) return;
      if (scrollRef.current) {
        await scanTween({
          scrollEl: scrollRef.current,
          wrapEl: stageRef.current,
          setCursor,
          isCancelled: () => cancelled,
          onRaf: (id) => (raf = id),
        });
      }
      if (cancelled) return;
      setPhase("done");
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      timers.forEach((t) => clearTimeout(t));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showPage = phase === "page" || phase === "done";

  return (
    <div ref={stageRef} className="relative">
      <Chrome tabTitle={host} tabFavicon={faviconFor(url)} address={url} typedAddress={url} loading={phase === "loading"}>
        <div className="relative">
          <PageBody url={url} content={content} screenshot={screenshot} scrollRef={scrollRef} visible={showPage} />
          {!showPage && (
            <div className="text-foreground/35 absolute inset-0 flex flex-col items-center justify-center gap-2 text-xs">
              <Globe className="h-6 w-6 animate-pulse" />
              Opening {host}…
            </div>
          )}
        </div>
      </Chrome>
      <Cursor x={cursor.x} y={cursor.y} clicking={false} visible={cursorVisible} />
    </div>
  );
}

export function BrowserStage(
  props:
    | {
        kind: "search";
        query: string;
        results: WebSearchPayload["results"];
        visits?: FollowUp[];
        onComplete?: () => void;
        instant?: boolean;
      }
    | { kind: "read"; url: string; content: string; screenshot?: string },
) {
  if (props.kind === "search")
    return (
      <BrowserSession
        query={props.query}
        results={props.results}
        visits={props.visits ?? []}
        onComplete={props.onComplete}
        instant={props.instant}
      />
    );
  return <ReadStage url={props.url} content={props.content} screenshot={props.screenshot} />;
}
{% endraw %}
