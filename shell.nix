# Development shell for NixOS.
#
# The pip wheels for z3-solver and cvc5 ship prebuilt shared libraries that
# link against libstdc++.so.6, which NixOS does not provide in a global
# library path. This shell supplies Python and exposes the C++ runtime so the
# project's .venv works unchanged.
#
# It also provides Pono (the downstream model checker used for cross-checking
# accepted constraints and measuring verification time) and a TeX Live with
# the packages Slides/ needs.
#
#   nix-shell                      # enter the shell
#   nix-shell --run 'python -m pytest -q'
{ pkgs ? import <nixpkgs> { } }:

let
  # Official prebuilt HWMCC'25 binary from the stanford-centaur/pono GitHub
  # release "hwmcc25" (2025-09-19, branch hwmcc25-dev). It is statically
  # linked, so it needs no patching. v2.0.0 ships no binaries.
  pono = pkgs.stdenvNoCC.mkDerivation {
    pname = "pono";
    version = "hwmcc25";
    src = pkgs.fetchurl {
      url = "https://github.com/stanford-centaur/pono/releases/download/hwmcc25/pono";
      hash = "sha256-Xlsm1utxilSNPbYtfeddZutdtb8bgaKK5UGAPcsU0+Y=";
    };
    dontUnpack = true;
    installPhase = ''
      install -Dm755 $src $out/bin/pono
    '';
    meta.platforms = [ "x86_64-linux" ];
  };

  # Slides/ uses beamer with the vendored SimplePlus theme, tikz, listings,
  # booktabs and the AMS packages.
  tex = pkgs.texliveSmall.withPackages (ps: with ps; [
    beamer
    pgf
    listings
    booktabs
    amsmath
    amsfonts
    latexmk
  ]);
in
pkgs.mkShell {
  packages = [ pkgs.python313 tex ]
    ++ pkgs.lib.optional (pkgs.stdenv.hostPlatform.system == "x86_64-linux") pono;

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib  # libstdc++.so.6 for z3-solver / cvc5 wheels
    pkgs.zlib
  ];

  shellHook = ''
    if [ ! -d .venv ]; then
      echo "Creating .venv (run: pip install -e '.[dev,crosscheck]')"
      python -m venv .venv
    fi
    source .venv/bin/activate
  '';
}
