process PICARD_COLLECT0XOGMETRICS {
    container "ghcr.io/martinluttap/picard:2.26.10"

    input:
        path input_bam
        path input_bai
        path ref_known_sites
        path ref_known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict

    output:
        path "${input_bam.baseName}.oxometrics", emit: metrics

    script:
        """
        java -jar /usr/local/bin/picard.jar CollectOxoGMetrics OUTPUT=${input_bam.baseName}.oxometrics CONTEXTS=CCG DB_SNP=${ref_known_sites} INPUT=${input_bam} REFERENCE_SEQUENCE=${ref_fa} TMP_DIR=. USE_OQ=true VALIDATION_STRINGENCY=SILENT
        """
}