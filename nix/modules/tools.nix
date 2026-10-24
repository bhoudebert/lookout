# The tools every environment shares: the dev shell and the apps.
{ lib, ... }:
{
  perSystem =
    { pkgs, ... }:
    {
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
      ];
      # Native wheels (pydantic-core, ...) need the C++ runtime and zlib; NixOS has no global loader path.
      _module.args.libraryPath = lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
        pkgs.zlib
      ];
    };
}
