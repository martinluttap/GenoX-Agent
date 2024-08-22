process PICARD_VALIDATESAMFILE {
    container "ghcr.io/martinluttap/picard:2.26.10"

    input:
        path bam
        path bai

    output:
        path "${bam}.metrics", emit: metrics

    script:
        """
        java -jar /usr/local/bin/picard.jar  ValidateSamFile  IS_BISULFITE_SEQUENCED=false  OUTPUT=${bam}.metrics  IGNORE_WARNINGS=true  INDEX_VALIDATION_STRINGENCY=NONE  INPUT=${bam}  MAX_OUTPUT=100  MODE=VERBOSE  TMP_DIR=.  VALIDATE_INDEX=false  VALIDATION_STRINGENCY=STRICT
        """
}