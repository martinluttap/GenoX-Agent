INTERVAL=1
OUTNAME=docker_stats.csv

update_file() {
  docker stats --no-stream --format "table {{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}" | tee --append $OUTNAME;
  TIMESTAMP=$(date +'%s.%N')
  echo "timestamp=${TIMESTAMP}" | tee --append $OUTNAME;
}

while true;
do
  update_file &
  sleep $INTERVAL;
done