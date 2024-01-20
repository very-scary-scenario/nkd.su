{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = { self, flake-utils, nixpkgs, poetry2nix }:
  flake-utils.lib.eachDefaultSystem (system:
  let
    pkgs = nixpkgs.legacyPackages.${system};
    inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication overrides;
  in {
    packages = {
      nkdsu = mkPoetryApplication {
        projectDir = self;
        groups = [ "test" "linting" ];
        overrides = overrides.withDefaults (final: prev: {
          alabaster = prev.alabaster.override { preferWheel = true; };  # requires flit
          django-instant-coverage = prev.django-instant-coverage.override { preferWheel = true; };  # requires setuptools
          django-pipeline = prev.django-pipeline.override { preferWheel = true; };  # requires setuptools
          django-resized = prev.django-resized.override { preferWheel = true; };  # requires setuptools
          levenshtein = prev.levenshtein.override { preferWheel = true; };  # requires packaging
          types-ujson = prev.types-ujson.override { preferWheel = true; };  # requires setuptools
        });
      };
    };
    devShells.default = pkgs.mkShell {
      inputsFrom = [ self.packages.${system}.nkdsu ];
      packages = [ pkgs.poetry ];
    };
  }
  );
}
