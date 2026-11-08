(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_120 () (_ BitVec 16))
(declare-fun i_4 () (_ BitVec 1))
(declare-fun s_5 () (_ BitVec 1))
(assert
 (let ((?x1278 (ite (bvule s_120 ((_ zero_extend 15) (_ bv1 1))) (_ bv1 1) (_ bv0 1))))
 (let ((?x1512 (bvxor i_4 ?x1278)))
 (let ((?x911 (bvnot ?x1512)))
 (let ((?x548 (bvor ?x911 ?x911)))
 (and (= (bvor s_5 (bvnot (bvnot s_5))) (_ bv1 1)) (= ?x548 (_ bv1 1))))))))
(assert
 (let (($x1305 (= ((_ extract 15 1) s_120) (_ bv0 15))))
(not $x1305)))
(check-sat)
