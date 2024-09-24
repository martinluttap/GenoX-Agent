process GATK4_BASERECAL {
    container "ghcr.io/martinluttap/gatk:4.2.4.1-no-entrypoint"

    input:
        path input
        path input_bai
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibrator --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa}
        """
}

process GATK4_BASERECAL_SPARK_NO_LIMIT {
    container "ghcr.io/martinluttap/gatk:4.2.4.1-no-entrypoint"

    input:
      path input
        path known_sites
        path known_sites_tbi
        path ref_fa
        path ref_amb
        path ref_ann
        path ref_bwt
        path ref_fai
        path ref_pac
        path ref_sa
        path ref_dict
		
    output:
        path "${input.baseName}_bqsr.grp"	, emit: output_grp
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar BaseRecalibratorSpark --output ${input.baseName}_bqsr.grp --input ${input} --known-sites ${known_sites} --reference ${ref_fa} --spark-master local[92]
        """
}
