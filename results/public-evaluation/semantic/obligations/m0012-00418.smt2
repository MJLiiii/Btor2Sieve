(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x55 ((_ extract 69 16) i_40)))
 (let ((?x1420 ((_ extract 15 0) i_40)))
 (let ((?x150 (concat ?x1420 ?x55)))
 (let ((?x94 (bvor (bvlshr i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvshl i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x1034 (ite (and (distinct ?x94 ?x150) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x1034 (_ bv1 1)))))))))
(assert
 (let ((?x1420 ((_ extract 15 0) i_40)))
(let (($x31 (bvuge ?x1420 (_ bv1 16))))
(not $x31))))
(check-sat)
