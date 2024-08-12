import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { SAMTOOLS_SORT_NO_LIMIT as SAMTOOLS_SORT1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/samtools_sort.nf"
include { SAMTOOLS_SORT_NO_LIMIT as SAMTOOLS_SORT2 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/samtools_sort.nf"


REF_PATH = "/home/cc/nextflow/reference-files"
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')

num_threads = params.num_threads
READ_PATH = "/home/cc/nextflow/read-files/bams/1500MB/"

Date loadStart = new Date()
println ("Data loading started ...")
bam_file = Channel.fromPath(READ_PATH + '/SRR*.bam')

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
    SAMTOOLS_SORT1(
        bam_file
    )
    SAMTOOLS_SORT2(
        bam_file
    )
}