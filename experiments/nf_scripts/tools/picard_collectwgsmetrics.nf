process PICARD_COLLECTWGSMETRICS {
    container "ghcr.io/martinluttap/picard:2.26.10"

    input:
        path input_bam
        path input_bai
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict

    output:
        path "${input_bam.baseName}.metrics", emit: metrics

    script:
        """
        java -jar /usr/local/bin/picard.jar CollectWgsMetrics OUTPUT=${input_bam.baseName}.metrics INPUT=${input_bam} REFERENCE_SEQUENCE=${ref_fa} VALIDATION_STRINGENCY=SILENT
        """
}