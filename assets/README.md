Profile images are versioned here so viewing the README does not depend on external image services.

`scripts/update_profile.py` updates activity, stats, languages, and streak daily through `.github/workflows/profile-cards.yml`. It validates each response before replacing a file. A failed refresh keeps the last working card and fails the workflow visibly. Run it manually with `python3 scripts/update_profile.py` after authenticating `gh`, or use the workflow's Run workflow button.

The activity graph is rendered directly from GitHub's contribution calendar. Stats and languages use public repository data; no personal access token is stored or required. Cards are snapshots, not live counters.

Image sources:

- Stats and languages: https://github.com/anuraghazra/github-readme-stats
- Streak: https://github.com/DenverCoder1/github-readme-streak-stats
- Animated introduction: https://github.com/DenverCoder1/readme-typing-svg
- Header and footer: https://github.com/kyechan99/capsule-render
- Skill icons: https://github.com/tandpfun/skill-icons
- Contact badges: https://shields.io/

Header, footer, introduction, skill icons, and badges are static design assets. Update them only when changing the profile content or design.
