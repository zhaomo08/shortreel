# shortreel

> 中文说明见 [GitHub 仓库](https://github.com/zhaomo08/shortreel)。

A customized fork of ArcReel (upstream 0.34.0): an open-source, self-hosted AI video production workspace. Turn novels, finished screenplays, or product assets into character-consistent, controllable, cost-trackable short videos that remain editable.

- **Source**: https://github.com/zhaomo08/shortreel
- **Documentation**: the upstream docs at https://docs.arc-reel.com/en/ describe the core workflow shared with this fork; fork-only features (Google Flow round-trip, locked output language, four color themes, OpenAI TTS) are documented in the repository README.
- **License**: AGPL-3.0

## No published image for this fork

This fork does not publish a Docker image. `deploy/docker-compose.yml` builds from source (`build: ../`, the upstream image line is commented out) so frontend and backend stay in sync. Build and run it with Compose:

```bash
git clone https://github.com/zhaomo08/shortreel.git
cd shortreel/deploy

cp .env.example .env
docker compose up -d
```

On first start the build takes a while. For networks in mainland China, build with the Aliyun PyPI mirror:

```bash
docker compose build --build-arg UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple
```

Open <http://localhost:1241>. The default username is `admin`. If `AUTH_PASSWORD` is empty, a password is generated on first startup and written back to `deploy/.env`.

> Default Compose publishes port `1241` on all host interfaces. Do not expose it directly to the public Internet; before enabling remote access, configure authentication and use HTTPS, a VPN, or a secure tunnel.

For the complete first-run walkthrough see [Getting Started](https://docs.arc-reel.com/en/guide/getting-started); for production deployment, upgrades, backups, and reverse proxies see [Deployment and Operations](https://docs.arc-reel.com/en/ops/deployment).

## What you get

- **One production workflow**: turn novels, finished screenplays, or product assets into characters, scenes, props, storyboards, video clips, and final videos step by step.
- **Visual continuity with human control**: reuse reference assets across shots, review key stages, regenerate individual assets, and roll back to earlier versions.
- **Manageable models and costs**: configure text, image, video, and TTS capabilities in one place, then review estimated costs and actual usage.
- **Editable delivery**: render final videos directly or export Jianying drafts to refine subtitles, voice-over, pacing, and transitions.
- **Fork-only**: Google Flow task-package export/import, locked output language (zh/en/vi, fallback English), four color themes (darkroom / fixer / baryta / silver), and OpenAI TTS (`gpt-4o-mini-tts`, `tts-1`, `tts-1-hd`) in the model catalog.

## Support

Reproducible bugs and focused feature requests are welcome in [GitHub Issues](https://github.com/zhaomo08/shortreel/issues).
