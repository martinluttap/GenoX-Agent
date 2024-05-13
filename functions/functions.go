package functions

import "strconv"

func calculateNewPeriod(oldPeriod string) string {
	old, _ := strconv.ParseFloat(oldPeriod, 64)
	stepMs := int64(10000)
	new := strconv.FormatInt(int64(old)+stepMs, 10)

	return new
}
