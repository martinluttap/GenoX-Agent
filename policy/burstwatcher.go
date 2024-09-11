package policy

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"
)

const (
	msPerSecond int64 = 1e3
	usPerSecond int64 = 1e6
	nsPerSecond int64 = 1e9
)

type BurstWatcher struct {
	/* External information */
	periodNs           int64
	quotaNs            int64
	originalQuotaUs    int64
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
		maxBurstNs:         1000 * nsPerSecond / msPerSecond,
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
	b.periodNs = periodNs * 10
}

func (b *BurstWatcher) updateQuotaNs(quotaNs int64) {
	b.quotaNs = quotaNs
}

func (b *BurstWatcher) setOriginalQuotaUs(originalQuotaUs int64) {
	b.originalQuotaUs = originalQuotaUs
}

func (b *BurstWatcher) resetJiffy() {
	b.deltaJiffyNs -= b.jiffyForSchedNs
}

func (b *BurstWatcher) resetPeriodWatch() {
	b.deltaPeriodWatchNs -= b.periodNs
}

func (b *BurstWatcher) resetToOriginalQuota(containerDir string) error {
	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		// path/to/whatever does not exist
		return err
	}
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
		return openErr
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	for s.Scan() {
		newQuotaUs := strconv.FormatInt(b.originalQuotaUs, 10)
		fmt.Printf("[%s] old:%s,RESET,new:%s\n", time.Now().Format(time.RFC3339Nano), s.Text(), newQuotaUs)
		infile.WriteString(newQuotaUs)
	}

	return nil
}

func (b *BurstWatcher) applyBurst(containerDir string) error {
	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		// path/to/whatever does not exist
		return err
	}
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
		return openErr
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	for s.Scan() {
		oldQuotaUs, _ := (strconv.ParseInt(s.Text(), 10, 64))
		newQuotaUs := strconv.FormatInt(oldQuotaUs+(b.availBurstNs*usPerSecond/nsPerSecond), 10)
		fmt.Printf("[%s] old:%d,applied:%d,new:%s\n", time.Now().Format(time.RFC3339Nano), oldQuotaUs, b.availBurstNs, newQuotaUs)
		infile.WriteString(newQuotaUs)
	}
	b.availBurstNs = 0

	return nil
}
