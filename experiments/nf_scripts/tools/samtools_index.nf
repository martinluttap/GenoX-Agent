process SAMTOOLS_INDEX_NO_LIMIT {
    container "ghcr.io/martinluttap/samtools:1.9"

    input:
      path input_bam
	    path input_bai
    
    output:
      path "${input_bam.getBaseName()}.idxstats", emit: bam_index

    script:
      """
      samtools idxstats  -@ 96 ${input_bam} > ${input_bam.getBaseName()}.idxstats
      """
}
