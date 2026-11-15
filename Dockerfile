FROM archlinux:latest

RUN echo 'Server = http://192.168.1.19:30100/$repo/os/$arch' > /etc/pacman.d/mirrorlist
RUN echo '[multilib]' >> /etc/pacman.conf
RUN echo 'Include = /etc/pacman.d/mirrorlist' >> /etc/pacman.conf

RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm --needed base-devel git python3 sudo pacman-contrib

RUN useradd -m builduser && echo 'builduser ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builduser

WORKDIR /build
RUN mkdir -p /build/workspace && chown builduser:builduser /build/workspace
COPY aur_builder/ /build/aur_builder/
COPY runner.sh /build/runner.sh

ENTRYPOINT ["/build/runner.sh"]
