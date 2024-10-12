process GATK4_APPLYBQSR {
    container "ghcr.io/martinluttap/gatk:4.2.4.1-no-entrypoint"

    input:
        path bam
        path bai
        path bqsr_recal_file
		
    output:
        path "${bam.baseName}_out.bam"	, emit:out_bam
		
    script:
        """
        java -jar /usr/local/bin/gatk.jar ApplyBQSR --output ${bam.baseName}_out.bam --bqsr-recal-file ${bqsr_recal_file} --emit-original-quals true --input ${bam} --tmp-dir .
        """
}

process GATK4_APPLYBQSR_SPARK_NO_LIMIT {
    container "ghcr.io/martinluttap/gatk:4.2.4.1-no-entrypoint"

    input:
        path bam
        path bai
        path bqsr_recal_file
		
    output:
        path "${bam.baseName}_out.bam"	, emit:out_bam
				
    script:
        """
        java -jar /usr/local/bin/gatk.jar ApplyBQSRSpark --output ${bam.baseName}_out.bam --bqsr-recal-file ${bqsr_recal_file} --emit-original-quals true --input ${bam} --tmp-dir . --spark-master local[92]
        """
}
