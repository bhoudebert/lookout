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
      # nix run .#quality              the gate, as in CI
      # nix run .#lookout -- inbox     any command of the CLI, in the dev shell, from the repository
      apps = {
        lookout = justApp "lookout" "lookout" "The lookout command line: nix run .#lookout -- inbox -p P0";
        serve = justApp "serve" "serve" "Serve the API and the dashboard (build it first: just ui-build)";
        demo = justApp "demo" "demo" "Add demo items to the database";
        quality = justApp "quality" "quality" "Format, lint, types, contracts, tests with 100% coverage, docs, frontend";
        dev = justApp "dev" "dev" "Backend and frontend on demo data";
        doctor = justApp "doctor" "doctor" "Check environment, LLM endpoint and sources";
      };
    };
}
