package policy

import "time"

const (
	msPerSecond int64 = 1e3
	usPerSecond int64 = 1e6
	nsPerSecond int64 = 1e9
)

type BurstWatcher struct {
	/* External information */
	periodNs           int64
	quotaNs            int64
	periodWatchStartNs int64
	/* Configurable constants */
	maxBurstNs      int64
	jiffyForSchedNs int64 // 5ms (4ms +- variance, check kernel/sched/sched.c)
	/* Calculated values */
	deltaJiffyNs       int64 // To check elapsed jiffies
	bucketUsageNs      int64
	availBurstNs       int64
	deltaPeriodWatchNs int64
}

func NewBurstWatcher() BurstWatcher {
	burstWatcher := BurstWatcher{
		maxBurstNs:         100 * nsPerSecond / msPerSecond,
		jiffyForSchedNs:    5 * nsPerSecond / msPerSecond,
		periodWatchStartNs: time.Now().UnixNano(),
		deltaJiffyNs:       0,
		bucketUsageNs:      0,
		availBurstNs:       0,
		periodNs:           0,
		quotaNs:            0,
		deltaPeriodWatchNs: 0,
	}
	return burstWatcher
}

func (b BurstWatcher) hasJiffyElapsed() bool {
	return (b.deltaJiffyNs >= b.jiffyForSchedNs)
}

func (b BurstWatcher) hasPeriodElapsed() bool {
	return (b.deltaPeriodWatchNs >= b.periodNs)
}

func (b *BurstWatcher) addUsage(usageNs int64) {
	b.bucketUsageNs += usageNs
	b.availBurstNs += usageNs
	b.availBurstNs = min(b.availBurstNs, b.maxBurstNs)
}

func (b *BurstWatcher) addJiffyNs(wallNs int64) {
	b.deltaJiffyNs += wallNs
}

func (b *BurstWatcher) addPeriodWatchNs(wallNs int64) {
	b.deltaPeriodWatchNs += wallNs
}

func (b *BurstWatcher) updatePeriodNs(periodNs int64) {
	b.periodNs = periodNs
}

func (b *BurstWatcher) updateQuotaNs(quotaNs int64) {
	b.quotaNs = quotaNs
}

func (b *BurstWatcher) resetJiffy() {
	b.deltaJiffyNs -= b.jiffyForSchedNs
}

func (b *BurstWatcher) resetPeriodWatch() {
	b.deltaPeriodWatchNs -= b.periodNs
}
