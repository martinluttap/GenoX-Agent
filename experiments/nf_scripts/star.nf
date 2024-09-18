import groovy.time.TimeCategory 
import groovy.time.TimeDuration

include { STAR_NO_LIMIT_SIMPLE as STAR1 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/star.nf"
include { STAR_NO_LIMIT_SIMPLE as STAR2 } from "/home/cc/elastic-container/containermod/experiments/nf_scripts/tools/star.nf"

Date loadStart = new Date()
println ("Data loading started ...")

REF_PATH = "/home/cc/nextflow/reference-files"
ref_fa = Channel.fromPath(REF_PATH + '/*.fa')
ref_amb = Channel.fromPath(REF_PATH + '/*.amb')
ref_ann = Channel.fromPath(REF_PATH + '/*.ann')
ref_bwt = Channel.fromPath(REF_PATH + '/*.bwt')
ref_fai = Channel.fromPath(REF_PATH + '/*.fai')
ref_pac = Channel.fromPath(REF_PATH + '/*.pac')
ref_sa = Channel.fromPath(REF_PATH + '/*.sa')
ref_dict = Channel.fromPath(REF_PATH + '/*.dict')
genome_dir = Channel.fromPath(REF_PATH + '/star-2.7.5c_GRCh38.d1.vd1_gencode.v36')


/* Config */
READ_PATH = "/home/cc/nextflow/read-files/star/"
meta_id = Channel.of(READ_PATH.tokenize('/')[-1])
fastq_pair = Channel.fromFilePairs(READ_PATH + '/SRR*_{1,2}.{1,2}.fastq', flat: true)
                    .splitFastq(by: 5000000, limit:5000000, pe:true, file: true)

workflow {
    fastq_pair.view {
        "Input files: ${it}, num_files=${it.size()}"
    }.subscribe {
        Date loadEnd = new Date()

        TimeDuration td = TimeCategory.minus(loadEnd, loadStart)

        def logFile = new File("LoadDuration.txt")
        logFile.delete()
        logFile.append(td)
        println ("Loading done! Took " + td)
    }
    STAR1(
        fastq_pair, genome_dir
    )
    // STAR2(
    //     fastq_pair, genome_dir
    // )
}