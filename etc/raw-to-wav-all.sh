:
for d in data/*/; do
  n="$(basename "$d")"
  for f in "$d"*.raw; do
    if [ -f "$f" ]; then
      b="$(basename "$f" .raw)"
      sh -x -c "sox -b 16 -e signed -r 16000 -c 1 '$f' '$d$n-$b.wav' && rm -f '$f'"
    fi
  done
done
