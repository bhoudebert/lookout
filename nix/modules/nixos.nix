# A NixOS module that runs Lookout from its published container image (docs/guide/self-hosting.md):
#
#   inputs.lookout.url = "github:bhoudebert/lookout";
#   # in the system configuration:
#   imports = [ inputs.lookout.nixosModules.lookout ];
#   services.lookout = { enable = true; configFile = ./lookout.yaml; environmentFile = "/run/secrets/lookout.env"; };
#
# The dashboard has no login, so it listens on 127.0.0.1 unless you say otherwise: put an authenticating proxy in front.
{ inputs, self, ... }:
{
  flake.nixosModules.lookout =
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      cfg = config.services.lookout;
      backend = config.virtualisation.oci-containers.backend;
      # The container's user; the data folder must belong to it.
      uid = 10001;
    in
    {
      options.services.lookout = {
        enable = lib.mkEnableOption "Lookout, a self-hosted watch tower for feeds, releases and advisories";

        image = lib.mkOption {
          type = lib.types.str;
          default = "ghcr.io/bhoudebert/lookout:latest";
          description = "The container image. Pin a version tag to choose when updates happen.";
        };

        configFile = lib.mkOption {
          type = lib.types.path;
          example = lib.literalExpression "./lookout.yaml";
          description = ''
            Your lookout.yaml: sources, stack, interests. It is copied to the Nix store, so keep secrets out of it and
            use `environmentFile` (LOOKOUT_LLM_API_KEY, LOOKOUT_GITHUB_TOKEN).
          '';
        };

        environmentFile = lib.mkOption {
          type = lib.types.nullOr lib.types.path;
          default = null;
          example = "/run/secrets/lookout.env";
          description = "A file of `NAME=value` lines read by the container, kept out of the Nix store.";
        };

        dataDir = lib.mkOption {
          type = lib.types.path;
          default = "/var/lib/lookout";
          description = "Where the SQLite file lives. A copy of it is the whole backup.";
        };

        listenAddress = lib.mkOption {
          type = lib.types.str;
          default = "127.0.0.1";
          description = "The address the dashboard listens on. It has no login: leave it local or authenticate in a proxy.";
        };

        port = lib.mkOption {
          type = lib.types.port;
          default = 8899;
          description = "The port on the host.";
        };

        openFirewall = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = "Open the port in the firewall. Only sensible with a `listenAddress` that is not local and a proxy that authenticates.";
        };
      };

      config = lib.mkIf cfg.enable {
        virtualisation.oci-containers.containers.lookout = {
          inherit (cfg) image;
          ports = [ "${cfg.listenAddress}:${toString cfg.port}:8899" ];
          volumes = [
            "${cfg.dataDir}:/data"
            "${cfg.configFile}:/config/lookout.yaml:ro"
          ];
          environmentFiles = lib.optional (cfg.environmentFile != null) cfg.environmentFile;
          # Lets the container reach Ollama running on the host as http://host.docker.internal:11434.
          extraOptions = [ "--add-host=host.docker.internal:host-gateway" ];
        };

        systemd.tmpfiles.rules = [ "d ${cfg.dataDir} 0750 ${toString uid} ${toString uid} -" ];

        networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [ cfg.port ];

        # `lookout doctor`, `lookout inbox`, ... run inside the container.
        environment.systemPackages = [
          (pkgs.writeShellScriptBin "lookout" ''
            exec ${backend} exec -i lookout lookout "$@"
          '')
        ];
      };
    };

  # The module must at least evaluate: build a throwaway system around it and render the container it defines.
  perSystem =
    { pkgs, ... }:
    {
      checks.nixos-module =
        let
          system = inputs.nixpkgs.lib.nixosSystem {
            inherit (pkgs.stdenv.hostPlatform) system;
            modules = [
              self.nixosModules.lookout
              {
                services.lookout = {
                  enable = true;
                  configFile = ../../lookout.example.yaml;
                  environmentFile = "/run/secrets/lookout.env";
                };
                virtualisation.oci-containers.backend = "docker";
                boot.loader.grub.enable = false;
                fileSystems."/" = {
                  device = "none";
                  fsType = "tmpfs";
                };
                system.stateVersion = "26.05";
              }
            ];
          };
          container = system.config.virtualisation.oci-containers.containers.lookout;
        in
        pkgs.writeText "lookout-nixos-module.json" (
          builtins.toJSON {
            inherit (container) image ports volumes environmentFiles extraOptions;
            tmpfiles = system.config.systemd.tmpfiles.rules;
            hasCommand = builtins.any (p: (p.name or "") == "lookout") system.config.environment.systemPackages;
          }
        );
    };
}
