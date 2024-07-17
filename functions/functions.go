package functions

import (
	"fmt"
	"math"
	"math/rand/v2"
	"strconv"
)

type BucketRange[T, U any] struct {
	Begin T
	End   U
}

type StepBucket struct {
	bucket BucketRange[float64, float64]
	value  float64
}

func randRange(min, max int, r *rand.Rand) int {
	return r.IntN(max-min) + min
}

func GenerateBuckets() []StepBucket {
	END_DUR := 180
	V_MIN := 1
	V_MAX := 16
	H_MIN := 4
	H_MAX := 18

	totalSecs := 0
	buckets := make([]StepBucket, 0, END_DUR/H_MIN)

	r := rand.New(rand.NewPCG(1, 2))
	for totalSecs <= END_DUR {
		nextVStep := randRange(V_MIN, V_MAX, r)
		nextHStep := randRange(H_MIN, H_MAX, r)
		if totalSecs+nextHStep >= END_DUR {
			break
		} else {
			totalSecs += nextHStep
			if len(buckets) == 0 {
				bucketRange := BucketRange[float64, float64]{Begin: 0, End: float64(nextHStep)}
				stepBucket := StepBucket{bucket: bucketRange, value: float64(nextVStep)}
				buckets = append(buckets, stepBucket)
			} else {
				lastEnd := buckets[len(buckets)-1].bucket.End
				bucketRange := BucketRange[float64, float64]{Begin: lastEnd, End: lastEnd + float64(nextHStep)}
				stepBucket := StepBucket{bucket: bucketRange, value: float64(nextVStep)}
				buckets = append(buckets, stepBucket)
			}
		}
	}
	return buckets
}

/****************** FUNCTIONS ******************/

func CalculateNewPeriod(oldPeriod string) string {
	old, _ := strconv.ParseFloat(oldPeriod, 64)
	stepMs := int64(100000)
	new := strconv.FormatInt(int64(old)+stepMs, 10)

	return new
}

func RandomStep(x float64, buckets []StepBucket) string {
	fmt.Println(buckets)
	for _, e := range buckets {
		if (e.bucket.Begin <= x) && (x <= e.bucket.End) {
			return strconv.FormatInt(int64(e.value)*100000, 10)
		}
	}
	return strconv.FormatInt(int64(buckets[len(buckets)-1].value)*100000, 10)
}

func ContinuousIncrease(x float64) string {
	fmt.Printf("Function called for %f\n", x)

	TARGET_CORE := 16
	INIT_CORE := 1
	START_DUR := 1
	END_DUR := 180 // 3 minutes

	// m = (y2 - y1) / (x2 - x1)
	m := float64(TARGET_CORE-INIT_CORE) / float64(END_DUR-START_DUR)

	// y = mx + c
	c := float64(0)
	y := int64(((m * x) + c) * 100000) // match cpu.cfs_quota_us, default=100000

	// newPeriod := strconv.FormatFloat(y, 'f', 2, 64)
	fmt.Printf("m:%f, x:%f, c:%f, y:%d\n", m, x, c, y)

	return strconv.FormatInt(y, 10)
}

func SineWave(x float64) string {
	// Sine wav: (A * sin(2 * Pi * f + phase)) + yOffset
	MIN_CORE := 1
	INIT_CORE := 8
	// START_DUR := 1
	// END_DUR := 180 // 3 minutes
	QUOTA_ONE_CORE := 100000

	yOffset := float64(INIT_CORE)
	amplitude := math.Max(float64(INIT_CORE-MIN_CORE), float64(1)) // Don't hit < 1
	frequency := float64(0.05)
	phase := float64(0)

	y := (amplitude * math.Sin((2*math.Pi*frequency*x)+phase)) + yOffset
	return strconv.FormatInt(int64(y*float64(QUOTA_ONE_CORE)), 10)
}

/*********************************************************/
