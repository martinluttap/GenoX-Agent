process TRIMMOMATIC_NO_LIMIT {
    container "ghcr.io/martinluttap/trimmomatic:0.38"

    input:
        tuple val(meta), path(forward_fastq), path(reverse_fastq)
		
    script:
        """
        java -Xmx32G -jar /bin/trimmomatic.jar PE -threads 64 ${forward_fastq} ${reverse_fastq} -baseout ${forward_fastq.getBaseName()}.out TOPHRED33
        """        
}