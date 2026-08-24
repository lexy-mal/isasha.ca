
  # Personal Page Design

  This is a code bundle for Personal Page Design. The original project is available at https://www.figma.com/design/pvmYP9IBl2P1UxBYoZgZkf/Personal-Page-Design.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.

  ## App version footer

  The dance app (`public/projects/com.html`) shows a build number in the page footer. It is stamped automatically on each Cloudflare deploy (`npm run build` uses `git rev-list --count HEAD`).

  Optional — stamp `version.json` on every local commit:

  ```bash
  git config core.hooksPath .githooks
  ```
  