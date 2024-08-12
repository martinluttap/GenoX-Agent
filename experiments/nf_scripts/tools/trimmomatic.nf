process TRIMMOMATIC_NO_LIMIT {
    container "ghcr.io/martinluttap/trimmomatic:0.38"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
		
    script:
        """
        java -Xmx4G -jar /bin/trimmomatic.jar PE -threads 96 -baseout ${forward_fastq.getBaseName()}.fq.gz -validatePairs ${forward_fastq} ${reverse_fastq} TOPHRED33
        """        
}