#!/usr/bin/env bash
#
# <xbar.title>Colima</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>tsuno</xbar.author>
# <xbar.desc>Colima VM の状態と docker コンテナの起動状況をメニューバーに出す。</xbar.desc>
# <xbar.dependencies>colima,docker</xbar.dependencies>
#
# SwiftBar は最小限の PATH で plugin を起動するため、ここで解決先を明示する。
# home-manager profile → nix-darwin の per-user profile → homebrew の順に探す。
# 対象は colima の default profile のみ。

set -u

PATH="$HOME/.local/state/home-manager/gcroots/current-home/home-path/bin"
PATH="$PATH:/etc/profiles/per-user/$USER/bin:$HOME/.nix-profile/bin"
PATH="$PATH:/run/current-system/sw/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export PATH

# SwiftBar は login shell を経由しないため fish/config.fish の env は届かない。
# COLIMA_HOME を渡さないと colima は残存する ~/.colima を見てしまい、別 VM を
# 起動・参照することになる。fish/config.fish と同じ値をここでも明示する。
export COLIMA_HOME="$HOME/.config/colima"
export DOCKER_CONFIG="$HOME/.config/docker"
export DOCKER_HOST="unix://$HOME/.config/colima/default/docker.sock"

COLIMA="$(command -v colima || true)"
DOCKER="$(command -v docker || true)"
LAZYDOCKER="$(command -v lazydocker || true)"
WEZTERM="$(command -v wezterm || true)"

# SwiftBar の terminal=true は Terminal.app 固定で、使う terminal を選ぶ設定が
# ない。そこで wezterm があれば `wezterm start -- <cmd>` に投げ直す。
# 引数は param1.. に1個ずつ渡す（値を引用符で囲むので空白入りでも壊れない）。
# `wezterm start` に --hold 相当がないため、終了するコマンドは終わると同時に
# window が閉じる。docker logs -f や lazydocker は居座るので問題にならない。
#
# usage: term_line "<label>" "<extra params>" <cmd> [args...]
term_line() {
  label="$1"
  extra="$2"
  shift 2

  if [ -n "$WEZTERM" ]; then
    line="$label | $extra bash=$WEZTERM param1=start param2=--"
    i=3
  else
    line="$label | $extra terminal=true bash=$1"
    shift
    i=1
  fi

  for a in "$@"; do
    line="$line param$i=\"$a\""
    i=$((i + 1))
  done

  printf '%s\n' "$line"
}

if [ -z "$COLIMA" ]; then
  echo "colima | sfimage=exclamationmark.triangle sfcolor=red"
  echo "---"
  echo "colima not found in PATH | color=red"
  exit 0
fi

# PROFILE STATUS ARCH CPUS MEMORY DISK RUNTIME ADDRESS
IFS=' ' read -r _profile status arch cpus memory disk runtime address \
  <<<"$("$COLIMA" list 2>/dev/null | awk '$1 == "default" { $1 = $1; print }')"

spec="${arch:-?} / ${cpus:-?} CPU / ${memory:-?} / ${disk:-?}"

if [ "${status:-}" != "Running" ]; then
  echo "off | sfimage=shippingbox sfcolor=gray"
  echo "---"
  echo "Colima: ${status:-Unknown} | sfimage=circle.fill sfcolor=gray"
  echo "$spec | size=12 color=gray"
  echo "---"
  term_line "Start colima" "sfimage=play.fill refresh=true" "$COLIMA" start
  echo "Refresh | sfimage=arrow.clockwise refresh=true"
  exit 0
fi

# ここから colima 稼働中。docker が繋がらないケースもそのまま出す。
containers=""
docker_err=""
if [ -z "$DOCKER" ]; then
  docker_err="docker not found in PATH"
else
  if ! containers="$("$DOCKER" ps -a --format '{{.Names}}\t{{.State}}\t{{.Status}}\t{{.Image}}' 2>&1)"; then
    docker_err="$containers"
    containers=""
  fi
fi

if [ -n "$docker_err" ]; then
  echo "? | sfimage=shippingbox.fill sfcolor=orange"
  echo "---"
  echo "Colima: Running | sfimage=circle.fill sfcolor=green"
  echo "$spec / ${runtime:-?} | size=12 color=gray"
  echo "---"
  echo "docker unreachable | color=orange"
  echo "$docker_err | size=12 color=gray"
else
  total="$(printf '%s' "$containers" | grep -c . || true)"
  running="$(printf '%s' "$containers" | awk -F'\t' '$2 == "running"' | grep -c . || true)"

  echo "$running/$total | sfimage=shippingbox.fill sfcolor=green"
  echo "---"
  echo "Colima: Running | sfimage=circle.fill sfcolor=green"
  echo "$spec / ${runtime:-?} | size=12 color=gray"
  [ -n "${address:-}" ] && echo "Address: $address | size=12 color=gray"
  echo "---"
  if [ "$total" -eq 0 ]; then
    echo "No containers | color=gray"
  else
    echo "Containers ($running/$total running) | size=12 color=gray"
    while IFS=$'\t' read -r name state st image; do
      [ -n "$name" ] || continue
      if [ "$state" = "running" ]; then
        echo "$name | sfimage=circle.fill sfcolor=green"
        echo "--Stop | sfimage=stop.fill bash=$DOCKER param1=stop param2=\"$name\" terminal=false refresh=true"
      else
        echo "$name | sfimage=circle sfcolor=gray"
        echo "--Start | sfimage=play.fill bash=$DOCKER param1=start param2=\"$name\" terminal=false refresh=true"
      fi
      echo "--$st | size=12 color=gray"
      echo "--$image | size=12 color=gray"
      term_line "--Logs" "sfimage=doc.text" "$DOCKER" logs -f "$name"
    done <<<"$containers"
  fi
fi

echo "---"
[ -n "$LAZYDOCKER" ] && term_line "lazydocker" "sfimage=terminal" "$LAZYDOCKER"
echo "Stop colima | sfimage=stop.fill bash=$COLIMA param1=stop terminal=false refresh=true"
term_line "Restart colima" "sfimage=arrow.clockwise.circle refresh=true" "$COLIMA" restart
echo "Refresh | sfimage=arrow.clockwise refresh=true"
