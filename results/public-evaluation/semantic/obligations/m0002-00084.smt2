(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_117 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x52 (ite (bvule s_117 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
 (let ((?x8 (bvxor i_4 ?x52)))
 (let ((?x105 (bvnot ?x8)))
 (let ((?x86 (bvor ?x105 ?x105)))
 (and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x86 (_ bv1 1))))))))
(assert
 (let ((?x59 (bvnot s_5)))
(let ((?x60 (bvnot ?x59)))
(let ((?x61 (bvor s_5 ?x60)))
(let (($x443 (and (distinct ?x61 i_4) true)))
(not $x443))))))
(check-sat)
