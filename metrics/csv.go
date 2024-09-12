package metrics

import (
	"encoding/csv"
	"fmt"
	"os"
	"strings"
)

func prepPollingAllStats(containerDirs []string, outWriterDict map[string]*csv.Writer) []*os.File {

	csvFds := []*os.File{}
	// Check existence of container in map.
	// If no entry yet, create metrics file and save the pointer towards it.
	for _, containerDir := range containerDirs {
		if _, exists := outWriterDict[containerDir]; !exists {
			fmt.Println("Created new writer for ", containerDir)
			ss := strings.Split(containerDir, "/")
			cid := ss[len(ss)-1][:13] // Use first 12 chars as containerId to match Docker's stats
			outFile, err := os.Create(fmt.Sprintf("%s-all.csv", cid))
			if err != nil {
				panic(err)
			}
			csvFds = append(csvFds, outFile)
			writer := csv.NewWriter(outFile)
			defer writer.Flush()
			// this defines the header value and data values for the new csv file
			headers := []string{"timestampNs", "cid", "totalCpu", "quotaUs", "periodUs", "numPeriods", "trPeriods", "trTimeNs"}
			writer.Write(headers)
			outWriterDict[containerDir] = writer
		}
	}

	return csvFds
}

func prepPollingCpuStats(containerDirs []string, outWriterDict map[string]*csv.Writer) []*os.File {

	csvFds := []*os.File{}
	// Check existence of container in map.
	// If no entry yet, create metrics file and save the pointer towards it.
	for _, containerDir := range containerDirs {
		if _, exists := outWriterDict[containerDir]; !exists {
			fmt.Println("Created new writer for ", containerDir)
			ss := strings.Split(containerDir, "/")
			cid := ss[len(ss)-1][:5]
			outFile, err := os.Create(fmt.Sprintf("%s-cpu.csv", cid))
			if err != nil {
				panic(err)
			}
			// defer outFile.Close()
			csvFds = append(csvFds, outFile)
			writer := csv.NewWriter(outFile)
			defer writer.Flush()
			// this defines the header value and data values for the new csv file
			headers := []string{"timestampNs", "cid", "cidCpuPercent", "machineCpuPercent"}
			writer.Write(headers)
			outWriterDict[containerDir] = writer
		}
	}

	return csvFds
	// Build cid -> containerDir map to join DockerStats and KernelStats
	// cidToDirMap := map[string]string{}
	// ss := strings.Split(containerDir, "/")
	// cid := ss[len(ss)-1][:12]
	// cidToDirMap[cid] = containerDir
}
