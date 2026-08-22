from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.15 patch missing: {label}')


def patch_main() -> None:
    text = MAIN.read_text(encoding='utf-8')
    # Keep the existing secure device-flow backend, but make its operator-facing
    # error actionable now that the add-on exposes github_oauth_client_id again.
    old = (
        '                "GitHub one-click OAuth requires Jarvis to have a registered GitHub "\n'
        '                "OAuth/GitHub App client ID. This build has no centrally registered Jarvis "\n'
        '                "GitHub App, so OAuth cannot be started safely without one."'
    )
    new = (
        '                "GitHub OAuth is not configured. Add github_oauth_client_id to the "\n'
        '                "Jarvis add-on configuration using a GitHub OAuth App or GitHub App "\n'
        '                "with Device Flow enabled, then reload the plugin catalog."'
    )
    require(text, old, 'GitHub configuration error')
    text = text.replace(old, new, 1)
    text = text.replace('version="0.11.14"', 'version="0.11.15"')
    text = text.replace('"version": "0.11.14"', '"version": "0.11.15"')
    MAIN.write_text(text, encoding='utf-8')


def patch_index() -> None:
    text = INDEX.read_text(encoding='utf-8')

    old = '''    if (item.auth_mode === "github-oauth" && !item.oauth_available && install) {
      install.disabled = true;
      install.textContent = "GitHub OAuth unavailable";
      install.title =
        "This Jarvis build does not yet include a registered Jarvis GitHub OAuth application.";
    }'''
    new = '''    if (item.auth_mode === "github-oauth" && install) {
      if (item.oauth_available) {
        install.disabled = false;
        install.textContent = "Connect GitHub";
        install.title = "Sign in to GitHub, authorize Jarvis, then install this plugin disabled by default.";
      } else {
        install.disabled = true;
        install.textContent = "GitHub OAuth not configured";
        install.title =
          "Set github_oauth_client_id in the Jarvis add-on configuration using an app with Device Flow enabled.";
      }
    }'''
    require(text, old, 'GitHub catalog button state')
    text = text.replace(old, new, 1)

    old_status = '"GitHub OAuth is unavailable in this build because Jarvis does not yet have a registered GitHub OAuth application."'
    new_status = '"GitHub OAuth is not configured. Set github_oauth_client_id in the Jarvis add-on configuration, then reload the catalog."'
    require(text, old_status, 'GitHub click status')
    text = text.replace(old_status, new_status)

    # Make the authorization display clearer while preserving the existing device-flow logic.
    old_code = '''          `GitHub authorization code: <strong>${catalogEsc(start.user_code)}</strong> · ` +
          `<a href="${catalogEsc(start.verification_uri)}" target="_blank" rel="noopener">Open GitHub authorization</a>`;'''
    new_code = '''          `GitHub authorization code: <strong>${catalogEsc(start.user_code)}</strong> · ` +
          `A GitHub sign-in window has opened. If it did not open, ` +
          `<a href="${catalogEsc(start.verification_uri)}" target="_blank" rel="noopener">open GitHub authorization</a>.`;'''
    require(text, old_code, 'GitHub authorization status text')
    text = text.replace(old_code, new_code, 1)

    text = text.replace('HUD 0.11.14', 'HUD 0.11.15')
    INDEX.write_text(text, encoding='utf-8')


def verify() -> None:
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    required = (
        'version="0.11.15"',
        'github_oauth_client_id',
        'Device Flow enabled',
        'Connect GitHub',
        'GitHub OAuth not configured',
        'A GitHub sign-in window has opened',
        'HUD 0.11.15',
    )
    missing = [marker for marker in required if marker not in main and marker not in index]
    if missing:
        raise RuntimeError('Jarvis v0.11.15 verification failed: ' + ', '.join(missing))


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
