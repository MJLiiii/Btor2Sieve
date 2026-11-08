(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(declare-fun s_11 () (_ BitVec 1))
(assert
 (let ((?x5498 (bvnot s_11)))
 (let ((?x31 (bvor ?x5498 (bvnot (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1))))))
 (and (= ?x31 (_ bv1 1))))))
(assert
 (let (($x28 (= s_3 s_4)))
(let ((?x6796 (ite $x28 (_ bv1 1) (_ bv0 1))))
(let ((?x5498 (bvnot s_11)))
(let ((?x31 (bvor ?x5498 (bvnot ?x6796))))
(let (($x120 (= ?x31 ?x6796)))
(not $x120)))))))
(check-sat)
