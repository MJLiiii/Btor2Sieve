(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 1))
(declare-fun i_3 () (_ BitVec 1))
(assert
 (and (= (bvnot (bvand i_3 i_4)) (_ bv1 1))))
(assert
 (let ((?x967 (bvnot (bvand i_3 i_4))))
(let (($x550 (and (distinct ?x967 i_4) true)))
(not $x550))))
(check-sat)
