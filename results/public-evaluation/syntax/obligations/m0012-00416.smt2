(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x886 ((_ extract 69 16) i_40)))
 (let ((?x85 ((_ extract 15 0) i_40)))
 (let ((?x1460 (concat ?x85 ?x886)))
 (let ((?x186 (bvor (bvlshr i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvshl i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x1532 (ite (and (distinct ?x186 ?x1460) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x1532 (_ bv1 1)))))))))
(assert
 (let ((?x85 ((_ extract 15 0) i_40)))
(let (($x210 (and (distinct ?x85 (_ bv1 16)) true)))
(not $x210))))
(check-sat)
