process PICARD_MARKDUPLICATES {
    container "ghcr.io/martinluttap/picard:2.26.10"

    input:
        path bam

    output:
        path "${bam.getBaseName()}_out.bam", emit: outbam

    script:
        """
        java -jar /usr/local/bin/picard.jar MarkDuplicates INPUT=${bam} METRICS_FILE=${bam.getBaseName()}.metrics ASSUME_SORT_ORDER=queryname OUTPUT=${bam.getBaseName()}_out.bam TMP_DIR=. VALIDATION_STRINGENCY=STRICT
        """
}

process PICARD_MARKDUPLICATES_SPARK {
    container "ghcr.io/martinluttap/gatk:4.2.4.1"
    containerOptions '--cpus=1'
    cpus 1

    input:
        path bam
        val num_thread

    output:
        path "${bam.getBaseName()}_out.bam", emit: out_bam

    script:
        """
        java -jar /usr/local/bin/gatk.jar MarkDuplicatesSpark --input ${bam} --metrics-file ${bam.getBaseName()}.metrics --output ${bam.getBaseName()}_out.bam --tmp-dir . --read-validation-stringency STRICT --spark-master local[$num_thread]
        """
}
