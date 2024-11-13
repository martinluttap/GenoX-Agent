package metrics

import (
	"log"
	"os/exec"
	"strconv"
	"strings"
)

func BuildDockerStats(cidToDirMap map[string]string) map[string]DockerStats {
	/*
			CONTAINER ID   NAME                           CPU %     MEM USAGE / LIMIT     MEM %     NET I/O          BLOCK I/O     PIDS
		c1105f0ff4b6   nxf-ApNjNbCU6j9F7z3k015mW07X   375.73%   11.53GiB / 187.4GiB   6.15%     2.45kB / 0B      5.45GB / 0B   103
		678500ab3f33   cadvisor                       28.72%    270MiB / 187.4GiB     0.14%     5.13MB / 428MB   3.73MB / 0B   96
	*/
	// Execute command
	cmd := exec.Command("docker", "stats", "--no-stream")
	var out strings.Builder
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		log.Fatal(err)
	}
	// Capture and process output
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	_, data := lines[0], lines[1:]
	statsMap := map[string]DockerStats{}
	for _, d := range data {
		fields := strings.Fields(d)
		cid, name := fields[0], fields[1]
		cpuUsage, _ := strconv.ParseFloat(strings.TrimRight(fields[2], `%`), 64)
		containerDir := cidToDirMap[cid]
		statsMap[containerDir] = DockerStats{
			containerId:   cid,
			containerName: name,
			cpuUsage:      cpuUsage,
		}
	}

	return statsMap
}
