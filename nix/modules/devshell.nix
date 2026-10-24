_: {
  perSystem =
    {
      pkgs,
      tools,
      libraryPath,
      browsers,
      ...
    }:
    {
      devShells.default = pkgs.mkShell {
        name = "lookout-shell";
        packages = tools;

        # uv uses the Python from Nix and never downloads one (downloaded builds cannot run on NixOS).
        UV_PYTHON_DOWNLOADS = "never";
        UV_PYTHON = "${pkgs.python313}/bin/python3.13";
        LD_LIBRARY_PATH = libraryPath;

        # Browsers for the end-to-end journeys come from Nix; the npm package is pinned to the same version.
        PLAYWRIGHT_BROWSERS_PATH = "${browsers}";
        PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = "true";

        shellHook = ''
          if [ ! -d .venv ] || [ ! -d node_modules ]; then
            echo "first time here: run 'just setup' (uv sync, npm ci, git hooks)"
          fi
          export PATH="$PWD/.venv/bin:$PATH"
        '';
      };
    };
}
