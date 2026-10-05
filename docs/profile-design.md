# Das Profil pflegen

Das Profil verwendet eine eigene Pixel-P-Marke, Graphit und Offwhite als Flächen und Orange als Akzent. Die Illustration soll Mike erkennbar machen; die nativen Markdown-Texte erklären seine Arbeit und bleiben auch ohne Bilder lesbar. Projektbeschreibungen gehören deshalb in die README, nicht ausschließlich in Grafiken.

Alle Illustrationen liegen als lokale SVGs in `.github/assets/`. Der Generator `.github/scripts/render_profile.py` erstellt sie mit der Python-Standardbibliothek. Es gibt keine Grafikpakete, Statistikdienste, extern geladenen Schriften oder API-Abfragen für die Darstellung. Dark- und Light-Varianten werden über `<picture>` gewählt; der Hero hat zusätzlich schmale Varianten. Nur der Hero darf dezent animiert sein und muss `prefers-reduced-motion` respektieren.

## Änderungen

1. Profiltexte und Projektlinks in `README.md` bearbeiten. Nur öffentlich erreichbare Projekte vorstellen und deren aktuellen Stand sachlich beschreiben.
2. Grafiktexte, Geometrie und Farben im Generator bearbeiten, dann die SVGs neu erzeugen:

   ```sh
   python3 .github/scripts/render_profile.py
   ```

3. Die beiden Prüfungen ausführen:

   ```sh
   python3 .github/scripts/render_profile.py --check
   python3 .github/scripts/check_profile.py
   ```

4. README und geänderte SVGs gemeinsam übernehmen. Vorher die Darstellung in hellem und dunklem Modus sowie in einem schmalen Fenster ansehen. Zeilenumbrüche, Kontrast und Projektlinks prüfen; mit reduzierter Bewegung muss der Hero ruhig bleiben.

`--check` stellt sicher, dass die abgelegten Grafiken dem Generator entsprechen. `check_profile.py` prüft Bildpfade, alternative Bildtexte, XML, unerwünschte externe Ressourcen und das gemeinsame SVG-Budget von weniger als 120.000 Bytes. Diese Prüfungen ersetzen die Sichtprüfung nicht.

## Automatisierung

`profile-check.yml` prüft Pushes und Pull Requests mit dem Python des GitHub-Runners. Der Workflow hat nur Leserechte, installiert keine Python-Pakete und schreibt keine Commits. `actions/checkout` ist auf einen vollständigen Commit-SHA festgelegt und speichert keine Zugangsdaten für nachfolgende Schritte.

Der Checkout-Pin entspricht **v7.0.1** und wurde über den [offiziellen Git-Tag](https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1) geprüft: `3d3c42e5aac5ba805825da76410c181273ba90b1`. Bei einem bewussten Update den SHA erneut am offiziellen Repository überprüfen; einen Versionsnamen nicht ungeprüft übernehmen.
