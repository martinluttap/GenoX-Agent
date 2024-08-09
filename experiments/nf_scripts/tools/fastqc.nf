process FASTQC_NO_LIMIT {
    container "ghcr.io/martinluttap/fastqc:0.12.1"

    input:
        path(fastq_files)

    output:
        path "*_fastqc.zip"	, emit: OUTPUT
		
    script:
        """
        /usr/local/bin/fastqc ${fastq_files} --dir . --format fastq --kmers 7 --noextract --outdir . --threads 64
        """
}
