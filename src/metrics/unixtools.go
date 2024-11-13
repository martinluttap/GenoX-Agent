package metrics

import (
	"log"
	"os/exec"
	"strconv"
	"strings"
)

func executeCgtop(cgroup string) string {
	/*	Execute:
		systemd-cgtop -b -n 2 -d 25ms docker/6629b5c0395314ab47fd4dec05d71bea3657c0bfb8f6087feecbda6c225702ca
		---
		Output:
		ControlGroup 		 Tasks   %CPU   Memory  Input/s Output/s
		docker/6629b5...      99   25.7   257.3M        -        -
	*/
	cmd := exec.Command("systemd-cgtop", "-b", "-n", "2", "-d", "5ms", cgroup)
	var out strings.Builder
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		log.Fatal(err)
	}
	return out.String()
}

func GetProcStatCpuCgtop(containerDirs []string) map[string]float64 {
	/*	Execute:
		systemd-cgtop -b -n 2 -d 25ms docker/6629b5c0395314ab47fd4dec05d71bea3657c0bfb8f6087feecbda6c225702ca
		---
		Output:
		ControlGroup 		 Tasks   %CPU   Memory  Input/s Output/s
		docker/6629b5...      99   25.7   257.3M        -        -

		Return map {"docker/66...": 25.7}
	*/
	cgtopMap := map[string]float64{}
	for _, containerDir := range containerDirs {
		ss := strings.Split(containerDir, "/")
		cgroup := strings.Join(ss[len(ss)-2:], `/`)
		// We take 10 iterations with rate 0.1 ms, but it's possible that not all has cpu usage (or even any).
		// Thus, we either take the last value, or if there's no value at all, we repeat the process.
		cpuUsages := []string{}
		for len(cpuUsages) == 0 {
			out := executeCgtop(cgroup)
			allLines := strings.Fields(out)
			lineLen := 6
			for i := 0; i < len(allLines); i = i + lineLen {
				singleLine := allLines[i : i+lineLen]
				if singleLine[2] != `-` {
					cpuUsages = append(cpuUsages, singleLine[2])
				}
			}
		}
		val, _ := strconv.ParseFloat(cpuUsages[len(cpuUsages)-1], 64)
		cgtopMap[containerDir] = val
	}
	return cgtopMap
}
