# Exolon — Step 9 Rebase (test archive)

This is the first runnable archive from the new level-rebase branch.

Key changes in this archive:
- keeps the existing 125-zone project and original-visual pipeline;
- Zone 009 object placement is rebuilt from the reference TMX coordinates rather than the old source-marker approximation;
- Zone 009 pistons now use x=64/192, y=320 (not y=384);
- changing room is a real 32x80 rectangle at x=368, y=176 in Tiled coordinates;
- rectangle-object coordinate conversion is explicit, so tile objects and rectangles are no longer conflated;
- pistons are lethal when exposed (unless test Invulnerability is ON);
- pressing UP inside the changing room toggles Exoskeleton mode;
- Exoskeleton fires a double blaster and protects against mines/pistons;
- Restart/new session resets Exoskeleton;
- every application launch still starts from Zone 000; High Score persists.

Important: this archive is a runnable checkpoint of the rebase work, not the claim that every late-zone action is already audited.

## Rebase cabin fix

- Changing-room artwork is now pass-through scenery: its action trigger no longer remains hidden behind compiled static collision.
- The collision exclusion is applied by object type, so it affects every changing-room screen, not only Zone 009.
- UP inside a changing room/teleport is consumed as a contextual action and cannot become an accidental jump on the following fixed step.
