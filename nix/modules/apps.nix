_: {
  perSystem =
    { pkgs, lib, ... }:
    let
      # Run a just recipe inside the dev shell, so a developer and CI use exactly the same environment.
      justApp =
        name: recipe: description:
        let
          drv = pkgs.writeShellApplication {
            inherit name;
            runtimeInputs = [ pkgs.git ];
            text = ''
              root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
              cd "$root"
              exec nix develop "$root" --command just ${recipe} "$@"
            '';
          };
        in
        {
          type = "app";
          program = lib.getExe drv;
          meta.description = description;
        };
    in
    {
      # nix run .#quality   the gate, as in CI
      apps = {
        quality = justApp "quality" "quality" "Format, lint, types, contracts, tests with 100% coverage, docs, frontend";
        dev = justApp "dev" "dev" "Backend and frontend on demo data";
        doctor = justApp "doctor" "doctor" "Check environment, LLM endpoint and sources";
      };
    };
}
