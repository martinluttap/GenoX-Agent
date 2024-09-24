process PICARD_VALIDATESAMFILE {
    container "ghcr.io/martinluttap/picard:2.26.10"
    errorStrategy { 
        if (task.exitStatus == 0){
            'ignore;'
        } else if (task.exitStatus == 2) {
            'ignore'
        } else if (task.exitStatus == 3) {
            'ignore'
        } else {
            'terminate'
        }
    }

    input:
        path bam
        path bai

    output:
        path "${bam}.metrics", emit: metrics

    script:
        """
        # Success codes are [0, 2, 3]. This script will most likely produce 3. 

        trap 'if [[ \$? == '2' || \$? == '3' ]]; then exit 0; fi' EXIT

        java -jar /usr/local/bin/picard.jar  ValidateSamFile  IS_BISULFITE_SEQUENCED=false  OUTPUT=${bam}.metrics  IGNORE_WARNINGS=true  INDEX_VALIDATION_STRINGENCY=NONE  INPUT=${bam}  MAX_OUTPUT=100  MODE=VERBOSE  TMP_DIR=.  VALIDATE_INDEX=false  VALIDATION_STRINGENCY=STRICT 
        """
}