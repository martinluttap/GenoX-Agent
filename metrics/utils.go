package metrics

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"syscall"
)

// A utility to convert the values to proper strings.
func int8ToStr(arr []int8) string {
	b := make([]byte, 0, len(arr))
	for _, v := range arr {
		if v == 0x00 {
			break
		}
		b = append(b, byte(v))
	}
	return string(b)
}

func GetSystemHz() (int64, error) {
	var uname syscall.Utsname
	if err := syscall.Uname(&uname); err == nil {
		// extract members:
		// type Utsname struct {
		//  Sysname    [65]int8
		//  Nodename   [65]int8
		//  Release    [65]int8
		//  Version    [65]int8
		//  Machine    [65]int8
		//  Domainname [65]int8
		// }
		fmt.Println(
			int8ToStr(uname.Release[:]),
		)
	}
	kernelRelease := int8ToStr(uname.Release[:])
	fmt.Println("GetSystemHz()", kernelRelease)
	bootConfigFile, openErr := os.OpenFile(fmt.Sprintf("/boot/config-%s", kernelRelease), os.O_RDONLY, 0444)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer bootConfigFile.Close()

	// Get all procs associated with container
	s := bufio.NewScanner(bootConfigFile)
	s.Scan()
	fmt.Println("Test", s.Text())
	var hertz string
	for s.Scan() {
		fmt.Println(s.Text())
		if strings.Contains(s.Text(), "CONFIG_HZ=") {
			hertz = strings.Split(s.Text(), "=")[1]
			fmt.Println(hertz)
			break
		}
	}
	if hertz != "" {
		hzValue, _ := strconv.ParseInt(hertz, 10, 64)
		return hzValue, nil
	} else {
		return 0, errors.New("Failed to read system hertz!")
	}
}
