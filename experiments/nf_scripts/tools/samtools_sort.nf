process SAMTOOLS_SORT_NO_LIMIT {
    container "ghcr.io/martinluttap/samtools:1.9"

    input:
      path input_bam
		
    output:
      path "${input_bam.getBaseName()}_sorted.bam", emit: sorted_bam

    script:
      """
      samtools sort  -@ 96 -o ${input_bam.getBaseName()}_sorted.bam ${input_bam}
      """
        
}
