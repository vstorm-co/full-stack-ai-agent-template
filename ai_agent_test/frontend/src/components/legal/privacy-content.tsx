import Link from "next/link";

import { APP_NAME } from "@/lib/constants";

export function PrivacyBodyEn() {
  return (
    <>
      <p>
        This Privacy Policy explains how {APP_NAME} (&ldquo;we&rdquo;, &ldquo;us&rdquo;) collects,
        uses, shares, and protects information when you use the Service.
      </p>

      <h2>1. What we collect</h2>
      <h3>Information you provide</h3>
      <ul>
        <li>
          <strong>Account info</strong> — name, email, hashed password, optional avatar.
        </li>
        <li>
          <strong>Customer Data</strong> — prompts, documents you upload, chat conversations,
          knowledge base content.
        </li>
        <li>
          <strong>Billing info</strong> — handled by our payment processor (Stripe). We never see
          your card number.
        </li>
        <li>
          <strong>Support correspondence</strong> — when you email us.
        </li>
      </ul>
      <h3>Information collected automatically</h3>
      <ul>
        <li>
          <strong>Usage data</strong> — request paths, response times, feature usage, error stack
          traces.
        </li>
        <li>
          <strong>Device data</strong> — browser, OS, IP address (for security and rate limiting).
        </li>
        <li>
          <strong>Cookies</strong> — see our <Link href="/legal/cookies">Cookie Policy</Link>.
        </li>
      </ul>

      <h2>2. Why we use it</h2>
      <ul>
        <li>To operate, maintain, and improve the Service;</li>
        <li>To process subscriptions and prevent fraud;</li>
        <li>To send transactional email (account, billing, security alerts);</li>
        <li>To respond to support requests;</li>
        <li>To detect abuse and enforce our Terms.</li>
      </ul>

      <h2>3. AI processing</h2>
      <p>
        When you use AI features, your prompts and the relevant context are sent to our configured
        model providers (e.g. OpenAI, Anthropic, Google) for processing. We choose providers that
        contractually agree not to use your data for training.
      </p>
      <p>
        <strong>We don&apos;t train any of our own models on your data.</strong>
      </p>

      <h2>4. Data sharing</h2>
      <p>We share data only with:</p>
      <ul>
        <li>
          <strong>Sub-processors</strong> we use to operate the Service (hosting, model providers,
          payment processor, email delivery, error monitoring). A current list is available on
          request.
        </li>
        <li>
          <strong>Authorities</strong> if required by law, but we&apos;ll push back where we can and
          notify affected users where legally permitted.
        </li>
        <li>
          <strong>An acquirer</strong> in the event of a merger or sale, with continuing obligations
          under this Policy.
        </li>
      </ul>

      <h2>5. Retention</h2>
      <p>
        We keep Customer Data for as long as your account is active. After deletion, backups are
        purged within 30 days. Logs and metrics are retained up to 90 days for security and
        operational analysis.
      </p>

      <h2>6. Your rights</h2>
      <p>
        Depending on where you live, you may have rights to access, correct, delete, or export your
        personal data, and to object to or restrict certain processing. Email{" "}
        <a href="mailto:privacy@example.com">privacy@example.com</a> to exercise them. We respond
        within 30 days.
      </p>

      <h2>7. International transfers</h2>
      <p>
        We host primarily in the EU. Where data is processed outside your country, we rely on
        standard contractual clauses or equivalent safeguards.
      </p>

      <h2>8. Security</h2>
      <p>
        We use TLS in transit, AES-256 at rest, role-based access control, and audit-logged admin
        actions. See the <Link href="/security">Security page</Link> for details.
      </p>

      <h2>9. Children</h2>
      <p>
        The Service isn&apos;t directed to children under 16. We don&apos;t knowingly collect
        information from them.
      </p>

      <h2>10. Changes</h2>
      <p>
        We&apos;ll notify you in-app or via email before any material change takes effect. Continued
        use after the effective date constitutes acceptance.
      </p>

      <h2>11. Contact</h2>
      <p>
        Questions or requests: <a href="mailto:privacy@example.com">privacy@example.com</a>.
      </p>
    </>
  );
}

export function PrivacyBodyPl() {
  return (
    <>
      <p>
        Niniejsza Polityka Prywatności wyjaśnia, jak {APP_NAME} (&bdquo;my&rdquo;,
        &bdquo;nas&rdquo;) zbiera, używa, udostępnia i chroni informacje gdy korzystasz z Usługi.
      </p>

      <h2>1. Co zbieramy</h2>
      <h3>Informacje, które podajesz</h3>
      <ul>
        <li>
          <strong>Dane konta</strong> — imię, email, zhashowane hasło, opcjonalny avatar.
        </li>
        <li>
          <strong>Dane Klienta</strong> — prompty, wgrywane dokumenty, rozmowy z czatu, zawartość
          baz wiedzy.
        </li>
        <li>
          <strong>Dane do płatności</strong> — obsługiwane przez naszego processora płatności
          (Stripe). Nigdy nie widzimy numeru Twojej karty.
        </li>
        <li>
          <strong>Korespondencja ze wsparciem</strong> — gdy do nas piszesz.
        </li>
      </ul>
      <h3>Informacje zbierane automatycznie</h3>
      <ul>
        <li>
          <strong>Dane użycia</strong> — ścieżki requestów, czasy odpowiedzi, użycie funkcji, stack
          traces błędów.
        </li>
        <li>
          <strong>Dane urządzenia</strong> — przeglądarka, OS, adres IP (do bezpieczeństwa i rate
          limitingu).
        </li>
        <li>
          <strong>Cookies</strong> — zobacz naszą{" "}
          <Link href="/legal/cookies">Politykę Cookies</Link>.
        </li>
      </ul>

      <h2>2. Po co tego używamy</h2>
      <ul>
        <li>by obsługiwać, utrzymywać i ulepszać Usługę;</li>
        <li>by przetwarzać subskrypcje i zapobiegać oszustwom;</li>
        <li>by wysyłać emaile transakcyjne (konto, płatności, alerty bezpieczeństwa);</li>
        <li>by odpowiadać na zgłoszenia wsparcia;</li>
        <li>by wykrywać nadużycia i egzekwować nasz Regulamin.</li>
      </ul>

      <h2>3. Przetwarzanie AI</h2>
      <p>
        Gdy korzystasz z funkcji AI, Twoje prompty i odpowiedni kontekst są wysyłane do
        skonfigurowanych dostawców modeli (np. OpenAI, Anthropic, Google) w celu przetwarzania.
        Wybieramy dostawców, którzy umownie zgadzają się nie używać Twoich danych do treningu.
      </p>
      <p>
        <strong>Nie trenujemy żadnego z naszych modeli na Twoich danych.</strong>
      </p>

      <h2>4. Udostępnianie danych</h2>
      <p>Udostępniamy dane tylko:</p>
      <ul>
        <li>
          <strong>Sub-processorom</strong> używanym do obsługi Usługi (hosting, dostawcy modeli,
          processor płatności, dostawa email, monitoring błędów). Aktualna lista dostępna na
          życzenie.
        </li>
        <li>
          <strong>Organom</strong> jeśli wymaga tego prawo, ale walczymy gdzie możemy i powiadamiamy
          dotkniętych użytkowników gdzie jest to prawnie dozwolone.
        </li>
        <li>
          <strong>Nabywcy</strong> w przypadku fuzji lub sprzedaży, z zachowaniem zobowiązań tej
          Polityki.
        </li>
      </ul>

      <h2>5. Retencja</h2>
      <p>
        Przechowujemy Dane Klienta tak długo jak konto jest aktywne. Po usunięciu konta backupy są
        usuwane w ciągu 30 dni. Logi i metryki są przechowywane do 90 dni dla bezpieczeństwa i
        analizy operacyjnej.
      </p>

      <h2>6. Twoje prawa</h2>
      <p>
        W zależności od miejsca zamieszkania, możesz mieć prawo do dostępu, sprostowania, usunięcia
        lub eksportu swoich danych osobowych, a także do sprzeciwu lub ograniczenia określonego
        przetwarzania. Napisz na <a href="mailto:privacy@example.com">privacy@example.com</a> by je
        zrealizować. Odpowiadamy w ciągu 30 dni.
      </p>

      <h2>7. Transfery międzynarodowe</h2>
      <p>
        Hostujemy głównie w UE. Tam, gdzie dane są przetwarzane poza Twoim krajem, opieramy się na
        standardowych klauzulach umownych lub równoważnych zabezpieczeniach.
      </p>

      <h2>8. Bezpieczeństwo</h2>
      <p>
        Używamy TLS in transit, AES-256 in rest, role-based access control oraz audit-logged akcji
        administracyjnych. Szczegóły na <Link href="/security">stronie Bezpieczeństwo</Link>.
      </p>

      <h2>9. Dzieci</h2>
      <p>
        Usługa nie jest skierowana do dzieci poniżej 16 roku życia. Świadomie nie zbieramy od nich
        informacji.
      </p>

      <h2>10. Zmiany</h2>
      <p>
        Powiadomimy Cię w aplikacji lub mailem przed wejściem w życie jakichkolwiek istotnych zmian.
        Dalsze korzystanie po dacie wejścia w życie oznacza akceptację.
      </p>

      <h2>11. Kontakt</h2>
      <p>
        Pytania lub żądania: <a href="mailto:privacy@example.com">privacy@example.com</a>.
      </p>
    </>
  );
}
