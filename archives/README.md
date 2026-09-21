# Архивы исходников

Верbatim-снимки исходников Exolon, привезённые в репозиторий как shipped zip. Коммитится сам
архив, а не его распакованное содержимое: цель — сохранить воспроизведённое состояние, которое
Git-дерево не описывает, а не удвоить текущий код.

## Exolon-Step9-rebase-fixes000-012.zip

| | |
|---|---|
| Корень архива | `Exolon-Step9-rebase-fixes000-012/` |
| Состав | 306 файлов, 1 374 494 Б без сжатия, 677 383 Б в zip |
| SHA-256 | `316f5da4ec24b7ab8d52757da72658aa590bad1899705323937b400b84da2a22` |
| Самый свежий файл внутри | `README.md`, 2026-09-19 12:12 UTC |
| Заимствован из | `Exolon-Step9-rebase-fixes000-012.zip` в корне рабочего дерева (untracked), 2026-09-21 |
| Целостность | `unzip -t` — No errors detected |

Только игровые исходники: `Exolon/`, `Exolon.xcodeproj/`, `README.md`,
`LEVEL_COMPILER_AUDIT.md`, `ORIGINAL_MECHANICS.md`. Ни `factory/`, ни `scripts/`, ни
`engineering/`, ни хуки в архиве не представлены.

### Чем отличается от `403eb13 Import Exolon Step 9 and factory 2.0.18 at 26a0d3d`

Архив не дублирует привезённое дерево. Замеренные отличия (сравнение `diff -rq` всего содержимого
архива с деревом `origin/main`):

- `Exolon/GameCore/GameScene.swift`
- `Exolon/GameCore/Levels/TMXLevelRuntime.swift`
- `Exolon/GameCore/Objects/LevelObstacles.swift`
- `Exolon/GameCore/Player/PlayerSpriteNode.swift`
- `Exolon/Resources/L01S05.tmx`, `L01S08.tmx`, `L01S09.tmx`, `L01S10.tmx`, `L01S11.tmx`, `L01S13.tmx`
- `Exolon.xcodeproj/project.pbxproj`
- `README.md`

`LEVEL_COMPILER_AUDIT.md` и `ORIGINAL_MECHANICS.md` побайтово совпадают с деревом. Наоборот
отсутствующих файлов нет: всё, что есть в `403eb13` по сравнившимся путям, есть и в архиве.

### Уникальное содержимое

`Exolon/Resources/vitorc_exoskeleton.png` (2 178 Б) и `Exolon/Resources/vitorc_original.png`
(2 127 Б) не закоммичены ни в один ref репозитория: `git log --all -- '*vitorc_exoskeleton*'
'*vitorc_original*'` пуст, а по всем деревам `Exolon/Resources` проходит единственный вариант
`vitorc.png` (2 280 Б). До этого коммита эти два спрайта существовали только внутри данного zip,
и архив остаётся их единственной версионированной копией.

### Как распаковать

```bash
C=$(git log --format=%H -1 -- archives/Exolon-Step9-rebase-fixes000-012.zip)
git show "$C:archives/Exolon-Step9-rebase-fixes000-012.zip" > /tmp/snapshot.zip
sha256sum /tmp/snapshot.zip   # сверить с SHA-256 выше
unzip -t /tmp/snapshot.zip && unzip /tmp/snapshot.zip -d /tmp/exolon-snapshot
```
