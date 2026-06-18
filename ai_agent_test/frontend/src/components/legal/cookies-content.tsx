export function CookiesBodyEn() {
  return (
    <>
      <p>
        We use cookies and similar technologies (collectively, &ldquo;cookies&rdquo;) to operate the
        Service and improve it. This page explains what we use and how to control it.
      </p>

      <h2>What is a cookie?</h2>
      <p>
        A small file your browser stores on your device when you visit a website. Cookies let us
        keep you logged in, remember preferences, and understand how features are used.
      </p>

      <h2>Categories</h2>
      <h3>Essential</h3>
      <p>
        Required for the Service to work. These can&apos;t be disabled. Examples: session token,
        CSRF token, preferred theme.
      </p>
      <ul>
        <li>
          <code>auth.session</code> — your authenticated session (httpOnly).
        </li>
        <li>
          <code>theme</code> — light/dark preference.
        </li>
        <li>
          <code>locale</code> — your selected language.
        </li>
      </ul>

      <h3>Analytics</h3>
      <p>
        Help us understand how the Service is used so we can improve it. We anonymize IP addresses
        and don&apos;t share with third parties for advertising.
      </p>
      <ul>
        <li>
          <code>analytics.session</code> — pageview and feature-usage counters.
        </li>
      </ul>

      <h3>Functional</h3>
      <p>Remember your choices to make the Service feel less repetitive. Optional.</p>
      <ul>
        <li>
          <code>onboarding.completed_at</code> — whether you finished the setup wizard.
        </li>
        <li>
          <code>cookie.consent</code> — your response to the cookie banner.
        </li>
      </ul>

      <h2>Your choices</h2>
      <p>
        You can accept, reject, or customize categories from the cookie banner shown on first visit.
        You can change your choice anytime from the link in the footer.
      </p>
      <p>
        You can also block cookies in your browser settings. Note: blocking essential cookies will
        break parts of the Service (e.g. you won&apos;t stay logged in).
      </p>

      <h2>Third-party cookies</h2>
      <p>
        We don&apos;t set advertising cookies. Some embedded content (videos, payment widgets) may
        set cookies — those are governed by their providers&apos; policies.
      </p>

      <h2>Contact</h2>
      <p>
        Questions: <a href="mailto:privacy@example.com">privacy@example.com</a>.
      </p>
    </>
  );
}

export function CookiesBodyPl() {
  return (
    <>
      <p>
        Używamy plików cookie i podobnych technologii (zbiorczo &bdquo;cookies&rdquo;) do obsługi
        Usługi i jej ulepszania. Ta strona wyjaśnia, czego używamy i jak to kontrolować.
      </p>

      <h2>Czym jest plik cookie?</h2>
      <p>
        Mały plik, który Twoja przeglądarka przechowuje na urządzeniu gdy odwiedzasz stronę. Cookies
        pozwalają nam utrzymywać Cię zalogowanego, pamiętać preferencje i rozumieć jak używane są
        funkcje.
      </p>

      <h2>Kategorie</h2>
      <h3>Niezbędne</h3>
      <p>
        Wymagane do działania Usługi. Nie można ich wyłączyć. Przykłady: token sesji, token CSRF,
        preferowany motyw.
      </p>
      <ul>
        <li>
          <code>auth.session</code> — Twoja uwierzytelniona sesja (httpOnly).
        </li>
        <li>
          <code>theme</code> — preferencja jasny/ciemny.
        </li>
        <li>
          <code>locale</code> — wybrany język.
        </li>
      </ul>

      <h3>Analityczne</h3>
      <p>
        Pomagają nam zrozumieć jak używana jest Usługa, żebyśmy mogli ją ulepszać. Anonimizujemy
        adresy IP i nie udostępniamy ich stronom trzecim do reklamy.
      </p>
      <ul>
        <li>
          <code>analytics.session</code> — licznik wyświetleń i użycia funkcji.
        </li>
      </ul>

      <h3>Funkcjonalne</h3>
      <p>Pamiętają Twoje wybory by Usługa nie była powtarzalna. Opcjonalne.</p>
      <ul>
        <li>
          <code>onboarding.completed_at</code> — czy ukończyłeś kreator setupu.
        </li>
        <li>
          <code>cookie.consent</code> — Twoja odpowiedź na banner cookies.
        </li>
      </ul>

      <h2>Twoje wybory</h2>
      <p>
        Możesz zaakceptować, odrzucić lub dostosować kategorie z bannera cookies pokazywanego przy
        pierwszej wizycie. Możesz zmienić wybór w każdej chwili z linku w stopce.
      </p>
      <p>
        Możesz też blokować cookies w ustawieniach przeglądarki. Uwaga: blokowanie niezbędnych
        cookies zepsuje części Usługi (np. nie pozostaniesz zalogowany).
      </p>

      <h2>Cookies stron trzecich</h2>
      <p>
        Nie ustawiamy reklamowych cookies. Niektóre osadzone treści (wideo, widgety płatności) mogą
        ustawiać cookies — podlegają one politykom swoich dostawców.
      </p>

      <h2>Kontakt</h2>
      <p>
        Pytania: <a href="mailto:privacy@example.com">privacy@example.com</a>.
      </p>
    </>
  );
}
