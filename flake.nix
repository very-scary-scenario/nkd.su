{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = { self, flake-utils, nixpkgs, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication;
      in {
        packages = {
          nkdsu = mkPoetryApplication {
            projectDir = self;

            # a lot won't build without this; poetry2nix won't pull in flit_core, django-pipeline doesn't see setuptools
            preferWheels = true;
          };
        };
        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.nkdsu ];
          packages = [ pkgs.poetry ];
        };
      }
    );
}
