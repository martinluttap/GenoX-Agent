package logger

import (
	"encoding/csv"
	"fmt"
	"os"
)

func WriteCsv(filePath string, headers []string, values [][]string) {
	if len(headers) != len(values[0]) {
		panic(fmt.Sprintf("WriteCSV: length of headers %d != length values[0] %d", len(headers), len(values[0])))
	}
	writer := csv.NewWriter(os.Stdout)

	writer.Write(headers)
	writer.Flush()
	writer.WriteAll(values)
}
