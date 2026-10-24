_: {
  perSystem =
    {
      pkgs,
      tools,
      libraryPath,
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

        shellHook = ''
          if [ ! -d .venv ] || [ ! -d node_modules ]; then
            echo "first time here: run 'just setup' (uv sync, npm ci, git hooks)"
          fi
          export PATH="$PWD/.venv/bin:$PATH"
        '';
      };
    };
}
