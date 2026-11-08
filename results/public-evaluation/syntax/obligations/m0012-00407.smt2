(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x203 ((_ extract 69 54) i_40)))
 (let ((?x369 ((_ extract 53 0) i_40)))
 (let ((?x106 (concat ?x369 ?x203)))
 (let ((?x178 (bvor (bvshl i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvlshr i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x72 (ite (and (distinct ?x178 ?x106) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x72 (_ bv1 1)))))))))
(assert
 (let ((?x203 ((_ extract 69 54) i_40)))
(let (($x318 (= ?x203 (_ bv32767 16))))
(not $x318))))
(check-sat)
