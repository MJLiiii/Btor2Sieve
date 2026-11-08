(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 1))
(assert
 (not (= (bvnot (bvand i_2 (bvnot i_2))) (_ bv1 1))))
(assert
 (let ((?x6 (bvnot i_2)))
(let (($x175 (and (distinct i_2 ?x6) true)))
(not $x175))))
(check-sat)
