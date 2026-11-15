# aur-builder

A docker container that functions as a CI\CD for building AUR packages for Arch Linux and uploading them to Gitea. Also supports building without upload so packags can be copied directly to a machine or uploaded to a different arch package repository.

While not recommended for most. This tool will also work outside of docker\directly on a local Arch box. This comes with the tradeoffs of installing build dependencies onto the same machine you are using, but it is an option if you wish because you would prefer the simplicity of it being on the base Arch Machine. You should seriously consider this if you are lacking a proper arch caching proxy (some recommended ones are under how to use).

## Why

By default many AUR packages are source packages and as a result these can take a long time to build. There is also a fairly well documented history of supply chain attacks and this allows you to have a local\frozen version with any modifications that you know is safe.

As to why to use this over just a standard AUR helper. This is more trackable what unofficial packages you have and makes it easier to regularly update the software.

For myself this project was built largely to allow automated rebuilds of dependencies for VR on Arch Linux as almost of the recommended packages are currently AUR packages and I would like to not be waiting on compilation to run\having to audit each package before upgrading.

## How it works

This project clones a repo of PKGBUILDs\SRCINFO where each pair is located in a seperate folder per project. Effectively it is the same view as if you had cloned the AUR packages git repos and placed them next to each other. It then builds a dependency graph and compiles\installs the respective dependencies in order. It is not able to resolve a dependency if it is not present in the subfolders provided and this is intentional so as to make sure that all repos have their full dependency tree available.

This project is also designed to run in a docker container which keeps the build environment clean and makes it trivial to run in something like k8s as a cronjob. This is actually how mine is deployed.

Personally, I keep local src mirrors through Gitea and keep assets that are static binaries on the network which can't (or shouldn't be rebuilt). This reduces bandwidth overall (as I build in a clean container each time), makes things a lot easier to trace\automate (as all the repos I am pulling are in the same gitea organization), and allows me to avoid network instability causing a failed build.

## How to use

I assume if you are using this you can read code because this tool also requires understanding how to modify a PKGBUILD in Arch Linux which does require a certain knowledge of code. As a result the expected usecase for this involves some reading of the code and changing a few options.

Take a look at `aur_builder/__main__.py` for all parameters available. I personally do not use all of these regularly, but you will likely want the `--force-upload`, `--gitea`, `--owner`, `--clone`, and `--token` params at a minimum. You will also likely find `--no-upload` to be useful if you do not run an Arch package repo. If you are managing a lot of custom AUR packages `--dry-run` will verify you do not have a broken dependency tree.

Take a look at the `Dockerfile` and please add any build deps you want to always be in the container\do not want loaded live. For me this is the multilib library as I am building a custom wine\proton version. I also using an internal arch package caching proxy (I use [flexo](https://github.com/nroi/flexo) though [pacoloco](https://github.com/anatol/pacoloco) is also a very solid option). For some documentation for the curious please take a look at the [package proxy cache](https://wiki.archlinux.org/title/Package_proxy_cache) docs for options on package caching as well as the [mirrors](https://wiki.archlinux.org/title/Mirrors) documentation for more general information. I opt to use a caching proxy largely for bandwidth\speed purposes as I am regularly rebuilding my packages\redownloading dependencies.

If you elect to upload to a [Gitea package registry](https://docs.gitea.com/usage/packages/arch/) you'll need to set this up per their docs. Do note this project will upload each package to a seperate registry so that multiple people can pick\choose what they want and\or use locally built packages through something like [yay](https://github.com/jguer/yay). In other words some people do mix and match packages between their own mirror, someone else's mirror, and locally built\compiled images. If you like all your packages to be in the same repo because you view the tradeoff\risk of someone loading all of your packages at once as work the simplicity of mirror setup you can also take a look at [this project](https://git.spatulaa.com/MayaTheShy/pkgpush) and just run this with `--no-upload`. On the same token if you run forgejo while both of these tools should in theory be compatible this is untested (though from my read of their docs the API [appears unchanged from gitea](https://forgejo.org/docs/latest/user/packages/arch/)). As for other package repositories you can just run with `--no-upload` and then run whatever script\tool you to choose to hand the uploads.

Modify the `runner.sh` to match your requirements. For example you may wish to handle uploading seperately or you may want different MAKEFLAGS set. You also likely will need to update the actual run command for the aur_builder itself.
