(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 1))
(declare-fun i_3 () (_ BitVec 1))
(assert
 (and (= (bvnot (bvand i_3 i_4)) (_ bv1 1))))
(assert
 (let ((?x830 (bvnot (bvand i_3 i_4))))
(let (($x223 (and (distinct ?x830 i_4) true)))
(not $x223))))
(check-sat)
