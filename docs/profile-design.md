# Profil: Gestaltung und Daten

Die animierte Pixelwelt und die Projektkarten entstehen als eigene lokale SVGs. Ein Python-Generator zeichnet sie mit der Standardbibliothek; externe Bild-Widgets, Grafikpakete und heruntergeladene Schriften sind nicht nötig. GitHub zeigt die Grafiken als Bilder an, deshalb gehören wichtige Informationen und Projektlinks zusätzlich in natives Markdown. Bewegung muss `prefers-reduced-motion` respektieren.

Die große Szene liegt in `.github/assets/world.svg`, die schmale Variante in `world-mobile.svg`. Projektkarten werden unter `.github/assets/projects/<Repo-ID>.svg` erzeugt. Numerische Repository-IDs bleiben auch bei einer Umbenennung stabil. Konfiguration und gespeicherte Daten liegen in `.github/profile/`; `public-repos.json` ist der validierte öffentliche Datenstand.

## Was automatisch aktualisiert wird

`sync_profile.py` liest die öffentlichen, eigenen Repositories des konfigurierten Accounts über die GitHub-API. Forks, archivierte oder deaktivierte Repositories und das Profilrepository selbst werden ausgeschlossen. Die Synchronisierung wählt daraus bis zu sechs Projekte für das Profil; der Renderer stellt diese Auswahl vollständig dar.

Ein vollständiger erfolgreicher Abruf ersetzt den gespeicherten Bestand. Neue Projekte können erscheinen, neue Namen und Links werden übernommen, und entfernte oder inzwischen private Projekte verschwinden aus der aktuellen Darstellung. Alte Git-Commits bleiben als Versionshistorie erhalten.

Bei einem fehlgeschlagenen oder unvollständigen Abruf bleibt der letzte gültige Datenstand erhalten; der Workflow meldet einen Fehler. `observed_at` ändert sich nur zusammen mit den gespeicherten Repository-Daten. **Datenstand** bezeichnet daher den Zeitpunkt der letzten übernommenen Datenänderung, nicht den letzten erfolgreichen Prüfversuch. Der Datenabruf ist keine Echtzeitverbindung.

## Gestaltung oder Texte ändern

Profilkonfiguration und Generator bearbeiten, anschließend lokal rendern und prüfen:

```sh
python3 .github/scripts/render_profile.py
python3 -m unittest discover -s .github/scripts -p 'test_*.py'
python3 .github/scripts/render_profile.py --check
python3 .github/scripts/check_profile.py
```

Der Renderer arbeitet offline aus dem gespeicherten Snapshot. Die README und ihre erzeugten Grafiken gemeinsam übernehmen; Änderungen an erzeugten Inhalten gehören in deren Quelle, sonst überschreibt der nächste Lauf sie.

Vor der Veröffentlichung Desktop und ein schmales Fenster ansehen, Projektlinks prüfen und reduzierte Bewegung testen. `--check` erkennt veraltete erzeugte Dateien. `check_profile.py` prüft lokale Bildpfade, alternative Bildtexte, SVG-XML, unerwünschte externe Ressourcen und ein gemeinsames SVG-Budget unter 400.000 Bytes. Die Prüfungen ersetzen keine Sichtprüfung.

## Workflows

- **Profile checks** prüft Pushes und Pull Requests ohne Schreibrechte oder Datenabrufe. Es verwendet Python direkt vom GitHub-Runner und installiert keine Python-Pakete.
- **Sync profile** läuft stündlich zur Minute 17 oder auf manuellen Aufruf, ausschließlich im Originalrepository auf dessen Default-Branch. Nur dieser Job hat Schreibrechte. Er ruft Daten ab, rendert, prüft und committet ausschließlich README, Snapshot und Grafiken, falls sich Dateien geändert haben.

Die Synchronisation ist auf einen schreibenden Lauf begrenzt. Ein gewöhnlicher `git push` veröffentlicht die geprüften Änderungen; ein zwischenzeitlich veränderter Remote-Branch führt zum Abbruch. Es gibt weder Force-Pushes noch einen automatischen Rebase über fremde Änderungen. Checkout hält seine Zugangsdaten nur im schreibenden Job bis zum abschließenden Cleanup vor; das API-Token wird nur dem Abrufschritt als Umgebungsvariable übergeben.

GitHub kann geplante Läufe verzögern oder bei hoher Last auslassen. In öffentlichen Repositories werden Zeitpläne nach 60 Tagen ohne Repository-Aktivität automatisch deaktiviert. Der [manuelle Workflow](https://github.com/PixelGG/PixelGG/actions/workflows/profile-sync.yml) erlaubt einen erneuten Abruf; einen deaktivierten Zeitplan zusätzlich in GitHub Actions wieder aktivieren. Diese Grenzen sind in der [offiziellen Schedule-Dokumentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) beschrieben.

Beide Workflows verwenden `actions/checkout` **v7.0.1**, festgelegt auf `3d3c42e5aac5ba805825da76410c181273ba90b1`. Der SHA wurde am [offiziellen Git-Tag](https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1) geprüft. Updates bewusst anhand des offiziellen Repositories durchführen.
