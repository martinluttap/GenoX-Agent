import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { SAMTOOLS_INDEX_NO_LIMIT as SAMTOOLS_INDEX1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/samtools_index.nf"
include { SAMTOOLS_INDEX_NO_LIMIT as SAMTOOLS_INDEX2 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/samtools_index.nf"

BAM_PATH = "/home/cc/nextflow/read-files/bams/1500MB/SRR062634_1500MB.bam"
BAI_PATH = "/home/cc/nextflow/read-files/samtools-index/SRR062634_1500MB.bai"

Date loadStart = new Date()
println ("Data loading started ...")
bam_file = Channel.fromPath(BAM_PATH)
bai_file = Channel.fromPath(BAI_PATH)

workflow {
    bam_file.view {
        "Input files: ${it}, num_files=${it.size()}"
    }.subscribe {
        Date loadEnd = new Date()

        TimeDuration td = TimeCategory.minus(loadEnd, loadStart)

        def logFile = new File("LoadDuration.txt")
        logFile.delete()
        logFile.append(td)
        println ("Loading done! Took " + td)
    }
    SAMTOOLS_INDEX1(
        bam_file,
        bai_file
    )
}