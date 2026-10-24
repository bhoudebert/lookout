# The tools every environment shares: the dev shell and the apps.
{ lib, ... }:
{
  perSystem =
    { pkgs, ... }:
    let
      # Chromium only: the journeys run in one browser, and the other two are hundreds of megabytes.
      browsers = pkgs.playwright-driver.browsers.override {
        withFirefox = false;
        withWebkit = false;
        withFfmpeg = false;
      };
    in
    {
      _module.args.browsers = browsers;
      _module.args.tools = with pkgs; [
        python313
        uv
        ruff
        pyright
        nodejs_24
        just
        git
        gh
        jq
        sqlite
        browsers
      ];
      # Native wheels (pydantic-core, ...) need the C++ runtime and zlib; NixOS has no global loader path.
      _module.args.libraryPath = lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
        pkgs.zlib
      ];
    };
}
